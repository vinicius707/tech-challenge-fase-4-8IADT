# Identidade — Auth JWT, refresh, logout e papéis

## Objetivo

Definir autenticação e autorização mínima do Limen para Operadores. A API deve
emitir JWT de acesso curto, permitir renovação via refresh token, invalidar
sessão no logout e distinguir os papéis `medico` e `admin`.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Escopo

- Modelo de Operador com username, senha bcrypt e papel.
- `POST /auth/login`, `POST /auth/refresh` e `POST /auth/logout`.
- Access token JWT de curta duração com claims de identidade e papel.
- Refresh token opaco, persistido e rotacionado a cada uso.
- Logout com blacklist/revogação do access token vigente e invalidação do
  refresh associado.
- Rate limit no login.
- Seed local dos Operadores `medico` e `admin`.
- Middleware/dependência que exige JWT em todas as rotas, exceto as públicas
  desta etapa.

Ficam fora desta etapa: Paciente, Rótulo Sensível, Registro de Auditoria de
reveal, frontend de login, OAuth/OIDC, MFA, rotação automática de chaves JWT e
RBAC com papéis além de `medico`/`admin`.

## ADRs aplicáveis

- [ADR 0004 — Auth JWT e papéis](../../docs/adr/0004-auth-jwt-papeis.md):
  define Operador autenticado por JWT e os papéis `medico` e `admin`.
- [ADR 0021 — Autorização na API](../../docs/adr/0021-auth-api-papeis.md):
  exige JWT em todas as rotas, exceto `/health` e `/auth/login`. Esta spec
  acrescenta `/auth/refresh` como rota pública autenticada por refresh token.
- [ADR 0006 — Endurecimento de segurança](../../docs/adr/0006-endurecimento-seguranca.md):
  exige bcrypt, JWT curto e rate limit no login. A menção a “refresh tokens fora
  do escopo” desta ADR é **supersedida** pelo plano do Épico 2 e por esta spec:
  refresh + logout com revogação entram no protótipo.
- [ADR 0009 — PostgreSQL + Redis](../../docs/adr/0009-postgres-redis.md):
  Operadores, refresh tokens e blacklist vivem no PostgreSQL; Redis permanece
  reservado à fila RQ.

## Modelo de domínio

**Operador**

- `id`: UUID.
- `username`: único, case-sensitive na comparação de login.
- `password_hash`: bcrypt.
- `role`: `medico` | `admin`.
- `created_at`, `updated_at`.

**Papéis**

| Papel    | Escopo nesta e nas próximas etapas                                      |
| -------- | ----------------------------------------------------------------------- |
| `medico` | Pacientes, Casos, Alertas e reveal de Rótulo Sensível                   |
| `admin`  | Mesmo escopo de `medico` + Falhas de Processamento e métricas futuras   |

Nesta etapa de Auth, a diferença prática de papel aparece apenas no claim JWT e
no seed; rotas de Paciente/DLQ serão protegidas nos épicos seguintes.

## Tokens

### Access token (JWT)

- Assinado com `JWT_SECRET` do ambiente.
- Expiração curta configurável (`JWT_ACCESS_TTL_SECONDS`, padrão sugerido: `900`).
- Claims mínimas:
  - `sub`: id do Operador
  - `username`
  - `role`
  - `iat`, `exp`
  - `jti`: identificador único do token
- Transportado em `Authorization: Bearer <access_token>`.

### Refresh token

- Valor opaco aleatório (não JWT).
- Persistido no PostgreSQL apenas como hash (ex.: SHA-256), nunca em claro.
- Expiração mais longa (`JWT_REFRESH_TTL_SECONDS`, padrão sugerido: `604800`).
- Vinculado a um Operador e a um `jti`/sessão.
- Rotacionado em cada `POST /auth/refresh`: o token usado é invalidado e um novo
  é emitido.
- Reuso de refresh já rotacionado/revogado deve falhar e invalidar a família da
  sessão associada.

### Logout / blacklist

- `POST /auth/logout` exige access token válido.
- O `jti` do access token entra em blacklist até o `exp` original.
- O refresh token da sessão correspondente é revogado.
- Requests posteriores com o mesmo access token retornam `401`.

## Rotas públicas e protegidas

Públicas nesta etapa:

- `GET /health`
- `POST /auth/login`
- `POST /auth/refresh`

Protegidas (Bearer access token obrigatório):

- `POST /auth/logout`
- qualquer outra rota futura da API

Ausência/invalidade/expiração/blacklist do access token → `401 Unauthorized`.
Access válido com papel insuficiente em rotas futuras → `403 Forbidden`.

## Contratos HTTP

### `POST /auth/login`

Request:

```json
{
  "username": "medico",
  "password": "medico-secret"
}
```

Sucesso `200 OK`:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque>",
  "token_type": "bearer",
  "expires_in": 900,
  "operator": {
    "id": "11111111-1111-1111-1111-111111111111",
    "username": "medico",
    "role": "medico"
  }
}
```

Credenciais inválidas → `401` com corpo genérico, sem indicar se o username
existe:

```json
{
  "detail": "Credenciais inválidas"
}
```

Rate limit excedido → `429`:

```json
{
  "detail": "Muitas tentativas de login. Tente novamente mais tarde."
}
```

### `POST /auth/refresh`

Request:

```json
{
  "refresh_token": "<opaque>"
}
```

Sucesso `200 OK`: mesmo formato do login, com novo access e novo refresh.

Refresh inválido, expirado, revogado ou reutilizado → `401` com
`{"detail": "Refresh token inválido"}`.

### `POST /auth/logout`

Headers: `Authorization: Bearer <access_token>`

Request opcional:

```json
{
  "refresh_token": "<opaque>"
}
```

Se o refresh for informado e pertencer ao Operador autenticado, deve ser
revogado junto com a blacklist do access. Se omitido, a implementação deve
revogar o refresh da sessão associada ao `jti` atual, quando existir.

Sucesso `204 No Content`.

Access ausente/inválido → `401`.

## Seed e configuração

Variáveis novas (documentar em `.env.example`):

- `JWT_SECRET`
- `JWT_ACCESS_TTL_SECONDS=900`
- `JWT_REFRESH_TTL_SECONDS=604800`
- `AUTH_LOGIN_RATE_LIMIT=5/minute`
- `SEED_MEDICO_USERNAME=medico`
- `SEED_MEDICO_PASSWORD=...` (somente local/demo)
- `SEED_ADMIN_USERNAME=admin`
- `SEED_ADMIN_PASSWORD=...` (somente local/demo)

O bootstrap/seed cria ou atualiza os dois Operadores de forma idempotente no
startup ou via comando documentado. Credenciais reais não entram no Git.

## Cenários de aceitação

### Cenário 1 — Login bem-sucedido de médico

**Dado** o Operador seed `medico` com senha válida  
**Quando** o cliente enviar `POST /auth/login` com username e senha corretos  
**Então** a resposta deve ser `200`  
**E** deve conter `access_token`, `refresh_token`, `token_type: "bearer"` e
`operator.role: "medico"`  
**E** o access token deve incluir claims `sub`, `username`, `role`, `exp` e
`jti`.

### Cenário 2 — Login bem-sucedido de admin

**Dado** o Operador seed `admin` com senha válida  
**Quando** o cliente enviar `POST /auth/login` com credenciais corretas  
**Então** a resposta deve ser `200`  
**E** `operator.role` deve ser `admin`.

### Cenário 3 — Credenciais inválidas

**Dado** um username inexistente ou senha incorreta  
**Quando** o cliente tentar login  
**Então** a resposta deve ser `401`  
**E** o `detail` deve ser genérico  
**E** a resposta não deve revelar hashes, existência do usuário nem stack
traces.

### Cenário 4 — Rate limit no login

**Dado** o limite configurado de tentativas por minuto  
**Quando** o mesmo originador exceder esse limite  
**Então** as tentativas seguintes devem responder `429`  
**E** nenhuma senha válida deve autenticar enquanto o limite estiver ativo.

### Cenário 5 — Refresh rotaciona tokens

**Dado** um login bem-sucedido  
**Quando** o cliente enviar `POST /auth/refresh` com o refresh emitido  
**Então** a resposta deve ser `200` com novos access e refresh  
**E** o refresh anterior deve deixar de ser aceito.

### Cenário 6 — Reuso de refresh revogado/rotacionado

**Dado** um refresh já usado em rotação  
**Quando** o cliente reenviar esse mesmo refresh  
**Então** a resposta deve ser `401`  
**E** a sessão/família associada deve ser invalidada.

### Cenário 7 — Rota protegida sem token

**Dado** uma rota protegida (ex.: `POST /auth/logout`)  
**Quando** o cliente chamar sem `Authorization`  
**Então** a resposta deve ser `401`.

### Cenário 8 — Access expirado ou adulterado

**Dado** um access token expirado ou com assinatura inválida  
**Quando** o cliente chamar uma rota protegida  
**Então** a resposta deve ser `401`.

### Cenário 9 — Logout invalida a sessão

**Dado** um Operador autenticado com access e refresh válidos  
**Quando** o cliente enviar `POST /auth/logout` com o Bearer access  
**Então** a resposta deve ser `204`  
**E** o mesmo access deve passar a receber `401`  
**E** o refresh associado deve falhar em `POST /auth/refresh`.

### Cenário 10 — Health permanece público

**Dado** a API em execução  
**Quando** o cliente consultar `GET /health` sem autenticação  
**Então** o endpoint deve continuar acessível conforme o contrato do Épico 1.

### Cenário 11 — Senha armazenada com bcrypt

**Dado** o seed ou a criação de um Operador  
**Quando** a senha for persistida  
**Então** o banco deve conter apenas `password_hash` bcrypt  
**E** a senha em claro nunca deve aparecer em logs nem no payload de resposta.

## Definição de pronto

- Spec aprovada como contrato antes da implementação T2.1–T2.4.
- Testes TDD cobrem login, refresh, logout, rate limit, seed e proteção de
  rotas.
- Access token curto e refresh rotativo funcionam localmente.
- Logout blacklista o access e revoga o refresh.
- `.env.example` e README documentam as novas variáveis sem secrets reais.
- `/health` permanece público; demais rotas exigem JWT.

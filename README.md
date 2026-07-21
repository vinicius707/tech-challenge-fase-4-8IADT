# Limen

Protótipo acadêmico da FIAP 8IADT — Fase 4 para análise multimodal e detecção
precoce de risco clínico.

> O Limen não é um dispositivo médico e não deve ser usado para decisões
> clínicas reais.

## Estado atual

O **Épico 1 — Fundação** e o **Épico 2 — Identidade e privacidade** estão
concluídos.

A entrega atual inclui a API de prontidão, infraestrutura local, autenticação
JWT (login, refresh, logout com blacklist, rate limit e seed), CRUD de Paciente
com Rótulo Sensível criptografado (Fernet), reveal com Registro de Auditoria e
cascata de schema para Caso stub.

Ainda não fazem parte da implementação: Casos multimodais, worker RQ, Azure,
frontend, Alertas SSE e o restante dos épicos 3–8.

## Fundação entregue

- FastAPI no backend.
- PostgreSQL preparado para o estado de domínio, com baseline Alembic
  `20260718_0001` e migrações de identidade até `20260721_0007`.
- Redis preparado como broker da futura fila RQ.
- MinIO S3-compatible para Artefatos.
- Bucket `limen` criado de forma idempotente.
- Docker Compose para execução local.

## Identidade e privacidade entregues

- Auth: `POST /auth/login`, `/auth/refresh`, `/auth/logout`; papéis `medico` e
  `admin`; rate limit e seed locais.
- Pacientes: CRUD em `/patients` com código `PAC-NNN`; Rótulo Sensível mascarado
  por padrão; `POST …/sensitive-label/reveal` com auditoria append-only.
- Schema: `patients`, `audit_records` e stub `cases` com
  `patient_id ON DELETE CASCADE`.
- Contratos: specs
  [`01-auth-login.md`](specs/epic-02-identity/01-auth-login.md) e
  [`02-paciente-privacidade.md`](specs/epic-02-identity/02-paciente-privacidade.md).

As decisões estão registradas em [`docs/adr/`](docs/adr/), especialmente as ADRs
[0001](docs/adr/0001-privacidade-paciente.md),
[0004](docs/adr/0004-auth-jwt-papeis.md),
[0005](docs/adr/0005-chave-pii-ambiente.md),
[0009](docs/adr/0009-postgres-redis.md),
[0011](docs/adr/0011-artefatos-minio.md) e
[0019](docs/adr/0019-observabilidade.md).

## Executar localmente

Pré-requisitos:

- Docker com Docker Compose v2.
- Portas 5432, 6379, 8000, 9000 e 9001 disponíveis, ou portas alternativas
  configuradas no `.env`.

Crie a configuração local e suba a stack:

```bash
cp .env.example .env
docker compose up --build --wait
```

O Compose aguarda PostgreSQL, Redis e MinIO, cria o bucket `limen`, aplica
`alembic upgrade head` e só então inicia o backend.

Verifique a prontidão:

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{
  "status": "ok",
  "checks": {
    "postgres": "ok",
    "redis": "ok",
    "minio": "ok"
  }
}
```

## Smoke test da fundação

O smoke test sobe a stack, aguarda os healthchecks e valida o contrato de
`/health`, a existência do bucket `limen` e o banco na revisão mais recente do
Alembic:

```bash
./scripts/smoke-foundation.sh
```

A stack permanece em execução para inspeção. Use `docker compose down` ao
terminar. O teste desta etapa não cria um Caso sintético; esse fluxo será
adicionado no Épico 8, conforme a ADR 0028.

Endpoints locais:

- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>
- Console MinIO: <http://localhost:9001>

Para encerrar sem apagar dados:

```bash
docker compose down
```

Para recriar o ambiente do zero, remova também os volumes. Esse comando apaga
o banco e todos os Artefatos locais:

```bash
docker compose down -v
```

## Configuração e secrets

O arquivo `.env.example` contém somente valores locais demonstrativos. O `.env`
é ignorado pelo Git e não deve conter credenciais reais versionadas. Em ambientes
compartilhados, substitua todas as senhas e use o mecanismo de secrets da
plataforma.

As variáveis disponíveis controlam credenciais, nomes de recursos, portas e o
timeout do healthcheck. `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`
também compõem automaticamente a URL usada pelo backend.

A autenticação usa as variáveis abaixo, documentadas na spec
[`specs/epic-02-identity/01-auth-login.md`](specs/epic-02-identity/01-auth-login.md):

- `JWT_SECRET`: chave de assinatura dos access tokens (obrigatória fora do dev).
- `JWT_ACCESS_TTL_SECONDS` (padrão `900`) e `JWT_REFRESH_TTL_SECONDS`
  (padrão `604800`): expiração dos tokens.
- `AUTH_LOGIN_RATE_LIMIT` (padrão `5/minute`): limite de tentativas de login
  por originador; excedente recebe `429`.
- `SEED_MEDICO_USERNAME`/`SEED_MEDICO_PASSWORD` e
  `SEED_ADMIN_USERNAME`/`SEED_ADMIN_PASSWORD`: Operadores seed criados de forma
  idempotente no startup. Somente para uso local/demo; se ausentes, nenhum
  Operador é criado.
- `PII_ENCRYPTION_KEY`: chave Fernet (URL-safe base64) para o Rótulo Sensível.
  Obrigatória apenas ao criar/atualizar Paciente **com** rótulo; sem ela, essas
  escritas respondem `503`. Gere com
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Contrato em
  [`specs/epic-02-identity/02-paciente-privacidade.md`](specs/epic-02-identity/02-paciente-privacidade.md).

Rotação manual da chave PII: pausar escritas de rótulo, recriptografar os
ciphertext com a nova chave (ou dual-key transitória, se implementada), validar
reveal/máscara e só então remover a chave antiga. Substituir a chave sem
recriptografar torna rótulos existentes ilegíveis.

## Testes do backend

Com Python 3.12 e `uv` instalados:

```bash
cd backend
uv sync
uv run pytest
```

## Integração contínua

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) executa em
pushes e pull requests. Nesta etapa ele instala as dependências pelo lockfile,
verifica a sintaxe Python como placeholder explícito de lint e executa pytest.
A [execução de fechamento do Épico 1](https://github.com/vinicius707/tech-challenge-fase-4-8IADT/actions/runs/29667220157)
foi concluída com sucesso.

Build e publicação de imagens, smoke com Caso sintético e frontend serão
adicionados no Épico 8.
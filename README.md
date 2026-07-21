# Limen

Protótipo acadêmico da FIAP 8IADT — Fase 4 para análise multimodal e detecção
precoce de risco clínico.

> O Limen não é um dispositivo médico e não deve ser usado para decisões
> clínicas reais.

Glossário de domínio: [`CONTEXT.md`](CONTEXT.md). Decisão de arquitetura:
[`docs/`](docs/README.md).

## Estado atual

O **Épico 1 — Fundação** e o **Épico 2 — Identidade e privacidade** estão
concluídos.

A entrega atual inclui a API de prontidão, infraestrutura local, autenticação
JWT (login, refresh, logout com blacklist, rate limit e seed), CRUD de Paciente
com Rótulo Sensível criptografado (Fernet), reveal com Registro de Auditoria e
cascata de schema para Caso stub.

Ainda não fazem parte da implementação: Casos multimodais, worker RQ, Azure,
frontend, Alertas SSE e o restante dos épicos 3–8. O próximo passo do plano é o
**Épico 3 — Núcleo Caso + fila**.

## O que já foi entregue

### Fundação (Épico 1)

- FastAPI no backend.
- PostgreSQL com migrações Alembic até `20260721_0007`.
- Redis preparado como broker da futura fila RQ.
- MinIO S3-compatible; bucket `limen` criado de forma idempotente.
- Docker Compose, smoke local e CI magra (pytest).

### Identidade e privacidade (Épico 2)

- Auth: `POST /auth/login`, `/auth/refresh`, `/auth/logout`; papéis `medico` e
  `admin`; rate limit e seed locais.
- Pacientes: CRUD em `/patients` com código `PAC-NNN`; Rótulo Sensível mascarado
  por padrão; `POST …/sensitive-label/reveal` com auditoria append-only.
- Schema: `operators`, `refresh_tokens`, `token_blacklist`, `patients`,
  `audit_records` e stub `cases` (`patient_id ON DELETE CASCADE`).
- Contratos SDD:
  [`01-auth-login.md`](specs/epic-02-identity/01-auth-login.md) e
  [`02-paciente-privacidade.md`](specs/epic-02-identity/02-paciente-privacidade.md).

## Executar localmente

Pré-requisitos: Docker Compose v2; portas 5432, 6379, 8000, 9000 e 9001 livres
(ou remapeadas no `.env`).

```bash
cp .env.example .env
docker compose up --build --wait
```

O Compose aguarda PostgreSQL, Redis e MinIO, cria o bucket `limen`, aplica
`alembic upgrade head`, faz o seed dos Operadores (se `SEED_*` estiver no `.env`)
e sobe o backend.

Endpoints locais:

| Recurso | URL |
| ------- | --- |
| API | <http://localhost:8000> |
| OpenAPI | <http://localhost:8000/docs> |
| Console MinIO | <http://localhost:9001> |

Encerrar sem apagar dados: `docker compose down`.  
Recriar do zero (apaga banco e Artefatos): `docker compose down -v`.

### Smoke da fundação

```bash
./scripts/smoke-foundation.sh
```

Valida `/health`, o bucket `limen` e a revisão Alembic. Não cobre login/Paciente
nem Caso sintético (este último entra no Épico 8).

## API — exemplos rápidos

Com a stack no ar e as credenciais seed do `.env.example`:

### Health (público)

```bash
curl -s http://localhost:8000/health | jq
```

### Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"medico","password":"medico_dev_only"}' \
  | jq -r .access_token)
```

### Criar Paciente com Rótulo Sensível

Requer `PII_ENCRYPTION_KEY` válida no ambiente do backend.

```bash
curl -s -X POST http://localhost:8000/patients \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sensitive_label":"Paciente Demo"}' | jq
```

A resposta vem mascarada (`sensitive_label_masked: "********"`). O texto em
claro só aparece no reveal:

```bash
PATIENT_ID=<uuid-retornado>
curl -s -X POST \
  "http://localhost:8000/patients/$PATIENT_ID/sensitive-label/reveal" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Rotas públicas nesta etapa: `GET /health`, `POST /auth/login`,
`POST /auth/refresh`. Demais rotas exigem Bearer access token.

## Configuração e secrets

O `.env.example` traz só valores locais demonstrativos. O `.env` é ignorado pelo
Git. Em ambientes compartilhados, troque todas as senhas e use secrets da
plataforma.

`POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` também montam a URL do
backend.

### Auth

Documentado em [`specs/epic-02-identity/01-auth-login.md`](specs/epic-02-identity/01-auth-login.md):

| Variável | Função |
| -------- | ------ |
| `JWT_SECRET` | Assinatura dos access tokens |
| `JWT_ACCESS_TTL_SECONDS` | TTL do access (padrão `900`) |
| `JWT_REFRESH_TTL_SECONDS` | TTL do refresh (padrão `604800`) |
| `AUTH_LOGIN_RATE_LIMIT` | Limite de login por IP (padrão `5/minute`) |
| `SEED_MEDICO_USERNAME` / `SEED_MEDICO_PASSWORD` | Seed do papel `medico` |
| `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD` | Seed do papel `admin` |

Sem `SEED_*`, nenhum Operador é criado no startup.

### Rótulo Sensível (PII)

Documentado em
[`specs/epic-02-identity/02-paciente-privacidade.md`](specs/epic-02-identity/02-paciente-privacidade.md):

| Variável | Função |
| -------- | ------ |
| `PII_ENCRYPTION_KEY` | Chave Fernet URL-safe base64 |

Obrigatória só ao criar/atualizar Paciente **com** rótulo (senão `503`). Sem
rótulo, o CRUD segue normalmente.

Gerar chave:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Rotação manual: pausar escritas de rótulo → recriptografar ciphertext (ou
dual-key transitória) → validar reveal/máscara → remover a chave antiga.
Trocar a chave sem recriptografar torna rótulos existentes ilegíveis.

## Testes do backend

```bash
cd backend
uv sync
uv run pytest
```

## Integração contínua

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em pushes
e PRs: `uv sync`, lint placeholder (sintaxe Python) e pytest. Build/publicação
de imagens, smoke com Caso sintético e frontend entram no Épico 8
(ADR [0028](docs/adr/0028-cicd-actions-ghcr.md)).

## Documentação

| Documento | Conteúdo |
| --------- | -------- |
| [`CONTEXT.md`](CONTEXT.md) | Linguagem ubíqua (Paciente, Caso, Risco, …) |
| [`docs/README.md`](docs/README.md) | Índice de ADRs e specs |
| [`specs/epic-01-foundation/`](specs/epic-01-foundation/) | Contrato Compose/health |
| [`specs/epic-02-identity/`](specs/epic-02-identity/) | Contratos auth e Paciente |
| [`.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md`](.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md) | Plano incremental dos épicos |

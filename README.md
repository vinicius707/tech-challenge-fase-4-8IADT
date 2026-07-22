# Limen

Protótipo acadêmico da FIAP 8IADT — Fase 4 para análise multimodal e detecção
precoce de risco clínico.

> O Limen não é um dispositivo médico e não deve ser usado para decisões
> clínicas reais.

Glossário de domínio: [`CONTEXT.md`](CONTEXT.md). Decisão de arquitetura:
[`docs/`](docs/README.md).

## Estado atual

Os **Épicos 1–4** estão concluídos (Fundação, Identidade, Núcleo Caso + fila e
Shell Frontend).

A entrega atual inclui autenticação JWT, Paciente com Rótulo Sensível, Caso com
modalidade `vitals` (Artefato no MinIO, outbox → RQ → Risco e Alerta v1 se ≥
MEDIO), worker e reconciler no Compose, e o shell Next.js (login, Pacientes,
Novo Caso e detalhe com polling).

Ainda não fazem parte da implementação: modalidades além de vitais, Azure,
Alertas SSE / feed, DLQ admin e o restante dos épicos 5–8.

## O que já foi entregue

### Fundação (Épico 1)

- FastAPI no backend.
- PostgreSQL com migrações Alembic até `20260721_0010`.
- Redis como broker da fila RQ.
- MinIO S3-compatible; bucket `limen` criado de forma idempotente.
- Docker Compose, smoke local e CI magra (pytest).

### Identidade e privacidade (Épico 2)

- Auth: `POST /auth/login`, `/auth/refresh`, `/auth/logout`; papéis `medico` e
  `admin`; rate limit e seed locais.
- Pacientes: CRUD em `/patients` com código `PAC-NNN`; Rótulo Sensível mascarado
  por padrão; `POST …/sensitive-label/reveal` com auditoria append-only.
- Contratos SDD:
  [`01-auth-login.md`](specs/epic-02-identity/01-auth-login.md) e
  [`02-paciente-privacidade.md`](specs/epic-02-identity/02-paciente-privacidade.md).

### Núcleo Caso + fila (Épico 3)

- Fixtures sintéticas de vitais (`normal` / `medium` / `high`) e script de
  calibração.
- Outbox Postgres → fila RQ `default`; serviços Compose `worker` e
  `outbox-reconciler`.
- `POST /patients/{id}/cases` (CSV + `Idempotency-Key`) e `GET /cases/{id}`.
- Pipeline: Artefato MinIO → AnomalyEngine → Fusion → Risco; Alerta v1 se
  `MEDIO` ou `ALTO` (dedupe; sem SSE).
- Schema: `cases`, `artifacts`, `case_modalities`, `outbox_jobs`, `alerts`.
- Contratos SDD em [`specs/epic-03-caso-fila/`](specs/epic-03-caso-fila/).

### Shell Frontend (Épico 4)

- Scaffold Next.js (App Router) + Tailwind + shadcn/ui em [`frontend/`](frontend/).
- Proxy `/api/*` → FastAPI (`BACKEND_URL`); serviço `frontend` no Compose.
- Login (Zustand), shell landmarks, Pacientes, Novo Caso vitais e detalhe de
  Caso com polling/Risco/Alertas.
- Baseline Lighthouse (sem gate): [`docs/perf/baseline/`](docs/perf/baseline/).
- Guia de uso + prints + troubleshooting:
  [`docs/frontend/`](docs/frontend/).
- Script de start: [`scripts/start-limen.sh`](scripts/start-limen.sh).
- Specs: [`specs/epic-04-shell-frontend/`](specs/epic-04-shell-frontend/).

## Executar localmente

Pré-requisitos: Docker Compose v2; portas 3000, 5432, 6379, 8000, 9000 e 9001
livres (ou remapeadas no `.env`).

### Forma recomendada (script)

```bash
./scripts/start-limen.sh
```

O script cria `.env` se necessário, sobe o Compose com `--build --wait`, valida
API + UI e imprime as URLs. Variantes: `--smoke`, `--down`, `--reset`.

Guia visual da UI: [`docs/frontend/guia-de-uso.md`](docs/frontend/guia-de-uso.md).  
Problemas comuns: [`docs/frontend/troubleshooting.md`](docs/frontend/troubleshooting.md).

### Forma manual

```bash
cp .env.example .env
docker compose up --build --wait
```

O Compose aguarda PostgreSQL, Redis e MinIO, cria o bucket `limen`, aplica
`alembic upgrade head`, faz o seed dos Operadores (se `SEED_*` estiver no `.env`)
e sobe o backend, o worker RQ, o reconciler de outbox e o frontend Next.

Endpoints locais:

| Recurso | URL |
| ------- | --- |
| UI | <http://localhost:3000> |
| API | <http://localhost:8000> |
| API via proxy UI | <http://localhost:3000/api/health> |
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

### Criar Caso com vitais

```bash
CASE=$(curl -s -X POST "http://localhost:8000/patients/$PATIENT_ID/cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-caso-1" \
  -F "file=@data/fixtures/vitals/vitals_medium.csv;type=text/csv")
echo "$CASE" | jq
CASE_ID=$(echo "$CASE" | jq -r .id)
```

Após o worker processar, o GET traz Risco e Alerta (se ≥ MEDIO):

```bash
curl -s "http://localhost:8000/cases/$CASE_ID" \
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

### Fila e outbox

| Variável | Função |
| -------- | ------ |
| `REDIS_URL` | Broker RQ |
| `RQ_QUEUE_NAME` | Fila do worker `default` (padrão `default`) |
| `RQ_VIDEO_QUEUE_NAME` | Fila do worker `worker-video` (padrão `video`) |
| `OUTBOX_RECONCILE_INTERVAL_SECONDS` | Intervalo do reconciler (padrão `5`) |

Contrato: [`specs/epic-03-caso-fila/02-outbox-rq.md`](specs/epic-03-caso-fila/02-outbox-rq.md).

### Frontend

| Variável | Função |
| -------- | ------ |
| `FRONTEND_PORT` | Porta publicada da UI (padrão `3000`) |
| `BACKEND_URL` | Origem FastAPI para o rewrite `/api` do Next |

Detalhes: [`frontend/README.md`](frontend/README.md). Login em `/login` (sessão
Zustand; proxy `/api/auth/*`).

## Testes do backend

```bash
cd backend
uv sync
uv run pytest
```

## Testes do frontend

```bash
cd frontend
npm ci
npm test
```

## Integração contínua

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em pushes
e PRs: `uv sync`, lint placeholder (sintaxe Python) e pytest. A baseline
Lighthouse em [`docs/perf/baseline/`](docs/perf/baseline/) é artefato versionado
**sem gate** neste épico. Build/publicação de imagens, smoke com Caso sintético
e frontend entram no Épico 8 (ADR [0028](docs/adr/0028-cicd-actions-ghcr.md)).

## Documentação

| Documento | Conteúdo |
| --------- | -------- |
| [`CONTEXT.md`](CONTEXT.md) | Linguagem ubíqua (Paciente, Caso, Risco, …) |
| [`docs/README.md`](docs/README.md) | Índice de ADRs e specs |
| [`specs/epic-01-foundation/`](specs/epic-01-foundation/) | Contrato Compose/health |
| [`specs/epic-02-identity/`](specs/epic-02-identity/) | Contratos auth e Paciente |
| [`specs/epic-03-caso-fila/`](specs/epic-03-caso-fila/) | Vitais, outbox/RQ, Caso → Risco/Alerta |
| [`specs/epic-04-shell-frontend/`](specs/epic-04-shell-frontend/) | Shell Next (scaffold → login → Pacientes) |
| [`frontend/`](frontend/) | App Next.js (Épico 4) |
| [`.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md`](.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md) | Plano incremental dos épicos |

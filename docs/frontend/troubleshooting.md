# Troubleshooting — rodar o Limen

Guia de diagnóstico para subir e usar o protótipo (Compose + UI + API).

> Não é um dispositivo médico.

## Índice rápido

| Sintoma | Ir para |
| ------- | ------- |
| Docker não sobe / daemon | [Docker Desktop](#1-docker-desktop-parado-ou-indisponível) |
| Porta em uso | [Portas](#2-porta-já-em-uso) |
| Build do frontend falha no `npm ci` | [Lockfile / Alpine](#3-build-do-frontend-falha-no-docker) |
| `/health` degradado | [Dependências](#4-health-degradado-postgresredisminio) |
| Login “Credenciais inválidas” | [Seed / JWT](#5-login-falha) |
| UI carrega mas lista de Pacientes quebra | [Proxy / BACKEND_URL](#6-proxy-api-e-backend_url) |
| Caso fica eternamente em `pending` | [Worker / outbox](#7-caso-não-sai-de-pendingprocessing) |
| Upload CSV → 503 | [MinIO](#8-upload-retorna-503) |
| Rate limit no login | [Rate limit](#9-too-many-requests-no-login) |
| Quer zerar o banco | [Reset](#10-reset-completo) |

## Comandos úteis

```bash
# Subir
./scripts/start-limen.sh

# Status
docker compose ps

# Logs (serviço)
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Health direto
curl -s http://localhost:8000/health | jq
curl -s http://localhost:3000/api/health | jq

# Encerrar / reset
./scripts/start-limen.sh --down
./scripts/start-limen.sh --reset
```

---

## 1. Docker Desktop parado ou indisponível

**Sintoma:** `Cannot connect to the Docker daemon` / `docker.sock`.

**O que fazer:**

1. Abra o Docker Desktop e aguarde “Engine running”
2. Confirme: `docker info`
3. Rode de novo: `./scripts/start-limen.sh`

No macOS: `open -a Docker` e espere ~30–60s.

---

## 2. Porta já em uso

**Sintoma:** `Bind for 0.0.0.0:3000 failed` (ou 8000/5432/…).

**O que fazer:**

1. Descubra o processo: `lsof -i :3000` (troque a porta)
2. Encerre o processo **ou** remapeie no `.env`:

```env
FRONTEND_PORT=3001
BACKEND_PORT=8001
POSTGRES_PORT=5433
```

3. `./scripts/start-limen.sh` de novo

Portas padrão: 3000 (UI), 8000 (API), 5432 (Postgres), 6379 (Redis),
9000/9001 (MinIO).

---

## 3. Build do frontend falha no Docker

**Sintoma:** `npm ci` reclama de packages ausentes no lock (ex.: `@emnapi/*`) no
Alpine Linux.

**O que fazer:**

- O `frontend/Dockerfile` usa `npm install` (mais tolerante a optional deps
  entre macOS e Linux). Se você reverteu para `npm ci` e quebrou, restaure o
  Dockerfile do repositório ou regenere o lock:

```bash
cd frontend
npm install
```

- Rebuild: `docker compose build --no-cache frontend && ./scripts/start-limen.sh`

---

## 4. Health degradado (Postgres/Redis/MinIO)

**Sintoma:** `GET /health` com `status` ≠ `ok` ou checks individuais falhando.

**O que fazer:**

```bash
docker compose ps
docker compose logs postgres redis minio | tail -n 80
```

- Aguarde o `--wait` terminar (o script usa timeout generoso)
- Confirme volumes e disco livre
- `minio-bootstrap` deve completar com sucesso (cria o bucket `limen`)

Smoke mínimo:

```bash
./scripts/smoke-foundation.sh
```

---

## 5. Login falha

**Sintoma:** mensagem genérica de credenciais inválidas.

Checklist:

1. `.env` existe e tem `SEED_MEDICO_*` / `SEED_ADMIN_*` (copie de `.env.example`)
2. Backend subiu **depois** do seed (entrypoint aplica migrações + seed)
3. Usuário/senha exatamente como no `.env` (padrão: `medico` / `medico_dev_only`)
4. `JWT_SECRET` definido (mínimo razoável para HS256)

Forçar recriação limpa (apaga dados):

```bash
./scripts/start-limen.sh --reset
./scripts/start-limen.sh
```

Teste via API:

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"medico","password":"medico_dev_only"}' | jq
```

---

## 6. Proxy `/api` e `BACKEND_URL`

**Sintoma:** UI abre, mas Pacientes/Casos falham; DevTools mostra 502/404 em
`/api/...`.

| Ambiente | `BACKEND_URL` esperado |
| -------- | ---------------------- |
| Compose (serviço `frontend`) | `http://backend:8000` |
| `npm run dev` no host | `http://localhost:8000` |

No Compose, a variável já vem do `.env.example`. Fora do Compose:

```bash
cd frontend
BACKEND_URL=http://localhost:8000 npm run dev
```

Confirme o proxy:

```bash
curl -s http://localhost:3000/api/health | jq
```

Deve espelhar o `/health` do backend.

---

## 7. Caso não sai de `pending`/`processing`

**Sintoma:** detalhe do Caso fica em skeleton / polling até o timeout de UX (120s)
e a mensagem “atualização automática foi pausada”.

Checklist:

```bash
docker compose ps worker outbox-reconciler
docker compose logs -f worker
docker compose logs -f outbox-reconciler
```

- `worker` precisa estar `Up` e consumindo a fila `default` (Redis)
- `outbox-reconciler` reenvia jobs pendentes periodicamente
- Fixtures inválidas / CSV vazio podem levar a `failed` (não a `done`)
- Se o log do worker mostrar `KeyError: outbox job not found` ou o Caso nunca
  mudar de `pending`, o job RQ pode não estar compartilhando o mesmo store de
  outbox/Caso que a API (processos separados). Recarregue `/casos/{id}` após
  corrigir o worker; o timeout de UX **pausa** o polling automático.

Após corrigir o worker, **recarregue** `/casos/{id}`.

---

## 8. Upload retorna 503

**Sintoma:** “Armazenamento indisponível” ao criar Caso.

- MinIO fora do ar ou bucket ausente
- Credenciais `MINIO_*` inconsistentes entre backend e MinIO

```bash
docker compose ps minio
docker compose logs minio minio-bootstrap | tail -n 50
curl -s http://localhost:8000/health | jq .checks.minio
```

---

## 9. Too Many Requests no login

**Sintoma:** várias tentativas rápidas falham mesmo com senha correta.

O rate limit padrão é `AUTH_LOGIN_RATE_LIMIT=5/minute`. Aguarde 1 minuto ou
ajuste no `.env` (somente local) e reinicie o backend:

```bash
docker compose up -d backend
```

---

## 10. Reset completo

Apaga volumes (Postgres + MinIO) e recria do zero:

```bash
./scripts/start-limen.sh --reset
./scripts/start-limen.sh
```

---

## Frontend só em modo desenvolvimento (sem Compose UI)

Útil para hot-reload, mantendo API/worker no Compose:

```bash
# Infra + API
docker compose up -d postgres redis minio minio-bootstrap backend worker outbox-reconciler

cd frontend
BACKEND_URL=http://localhost:8000 npm run dev
```

Abra <http://localhost:3000>. Não rode o serviço `frontend` do Compose na mesma
porta 3000.

---

## Ainda travado?

1. Colete: `docker compose ps` + últimos 100 linhas de `backend`/`worker`/`frontend`
2. Confirme `.env` (sem secrets reais commitados)
3. Consulte o glossário [`CONTEXT.md`](../../CONTEXT.md) e as specs em
   [`specs/epic-04-shell-frontend/`](../../specs/epic-04-shell-frontend/)

# Limen

Protótipo acadêmico da FIAP 8IADT — Fase 4 para análise multimodal e detecção
precoce de risco clínico.

> O Limen não é um dispositivo médico e não deve ser usado para decisões
> clínicas reais.

Glossário de domínio: [`CONTEXT.md`](CONTEXT.md). Decisão de arquitetura:
[`docs/`](docs/README.md). Diagramas da stack:
[`docs/architecture.md`](docs/architecture.md).

## Estado atual

Os **Épicos 1–7** estão concluídos. O **Épico 8 / E8.1** (publish GHCR + smoke
Caso vitais) também está concluído; resta **E8.2** (seed/notebooks/relatório/
roteiro).

A entrega atual inclui autenticação JWT, Paciente com Rótulo Sensível (reveal +
SR), Caso com modalidades `vitals`, `video`, `audio` e `prescriptions` (Artefatos
no MinIO, outbox → filas RQ `default` / `video` → Risco fundido e Alerta
versionado se ≥ MEDIO), Justificativa template, feed SSE de Alertas com toast
`aria-live="polite"`, Recharts lazy em Caso/Paciente, painel admin de Falhas,
Provedor de Áudio com CB/fallback, regras de Prescrição + seed multimodal, falha
parcial / reprocess, workers Compose, shell Next.js (tema dark/light), gate
Lighthouse no CI, publish GHCR em `main` e smoke Compose de Caso vitais
(`./scripts/smoke-caso-vitais.sh`).

Ainda não fazem parte da implementação: fechamento fino do README de entrega
E8.2 (T8.8); chamada Azure Speech real obrigatória no CI (`AZURE_ENABLED=false`).
Relatório: [`docs/relatorio-fase4.md`](docs/relatorio-fase4.md). Roteiro:
[`docs/demo/roteiro-video.md`](docs/demo/roteiro-video.md). Notebooks:
[`notebooks/`](notebooks/). Seed: `./scripts/seed-multimodal-demo.sh`.

## O que já foi entregue

### Fundação (Épico 1)

- FastAPI no backend.
- PostgreSQL com migrações Alembic até `20260722_0016` (inclui `justification`
  JSON no Caso, `provider`, idempotências de áudio/prescriptions).
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
- Baseline Lighthouse: [`docs/perf/baseline/`](docs/perf/baseline/) (gate no
  Épico 7 / E7.3).
- Guia de uso + prints + troubleshooting:
  [`docs/frontend/`](docs/frontend/).
- Script de start: [`scripts/start-limen.sh`](scripts/start-limen.sh).
- Specs: [`specs/epic-04-shell-frontend/`](specs/epic-04-shell-frontend/).

### Resiliência (Épico 5)

- Falha parcial: Caso pode fechar `done` com modalidades `failed`; fusão só
  sobre `done`.
- `POST /cases/{id}/reprocess` seletivo; Alertas versionados append-only.
- Filas RQ `default` + `video` (`worker-video`); retries transitórios e
  circuit breaker Azure (stub).
- Specs: [`specs/epic-05-resiliencia/`](specs/epic-05-resiliencia/).

### Modalidades — Vídeo (Épico 6 / E6.1)

- Fixtures AVI sintéticas (`physio` / `surgery_light`) + regeneração:
  [`data/fixtures/video/`](data/fixtures/video/).
- `POST /cases/{id}/modalities/video` (multipart + `Idempotency-Key`) → MinIO +
  job na fila `video`.
- Análise Postural (Pose) e Detecção em Cena (YOLO COCO + heurísticas);
  backends `synthetic` padrão (`LIMEN_POSE_BACKEND` / `LIMEN_YOLO_BACKEND`).
- Frames anotados como Artefatos `video_frame`; vídeo contribui ao Risco
  (fusão com vitais; falha parcial intacta).
- Spec:
  [`01-video-pose-yolo.md`](specs/epic-06-modalidades/01-video-pose-yolo.md).

### Modalidades — Áudio (Épico 6 / E6.2)

- Fixture WAV PCM sintética ≤60s + regeneração:
  [`data/fixtures/audio/`](data/fixtures/audio/).
- `POST /cases/{id}/modalities/audio` (multipart + `Idempotency-Key`) → MinIO +
  job na fila RQ `default` (não `video`).
- Analyzer local determinístico + cache SHA-256 + Azure Speech F0 **injetável**;
  circuit breaker (ADR 0015) força `local` sem rede.
- Badge `provider` (`azure` \| `local` \| `cache`) em `GET /cases/{id}`; áudio
  contribui ao Risco (fusão com vitais/vídeo; falha parcial intacta).
- CI/demo: `AZURE_ENABLED=false` (sem Azure real obrigatório).
- Spec:
  [`02-audio-azure.md`](specs/epic-06-modalidades/02-audio-azure.md).

### Modalidades — Prescrições + seed (Épico 6 / E6.3)

- Fixtures CSV `normal` / `medium` / `high` + catálogo sintético:
  [`data/fixtures/prescriptions/`](data/fixtures/prescriptions/).
- `POST /cases/{id}/modalities/prescriptions` (multipart + `Idempotency-Key`) →
  MinIO + job na fila RQ `default`.
- Regras determinísticas (dose / intervalo / medicamento inesperado) e desvio
  longitudinal vs. histórico do Paciente (ADR 0010).
- Contribui ao Risco (fusão; falha parcial intacta); timeout padrão 30s.
- Seed demo multimodal (vitals+vídeo+áudio+prescriptions):
  [`scripts/seed-multimodal-demo.sh`](scripts/seed-multimodal-demo.sh) (HTTP /
  Compose) ou
  [`scripts/seed_multimodal_demo.py`](scripts/seed_multimodal_demo.py)
  (`--memory` / `--http`).
- Spec:
  [`03-prescricoes-seed.md`](specs/epic-06-modalidades/03-prescricoes-seed.md).

### Alertas — Justificativa + SSE (Épico 7 / E7.1)

- Justificativa template determinística (sem LLM) no `GET /cases/{id}`:
  contribuições por modalidade `done`, pesos iguais, modalidades
  `failed`/`skipped` como indisponíveis; snapshot JSON persistido na fusão.
- UI em `/casos/[id]` (narrativa + lista de contribuições).
- `GET /alerts/stream` (SSE): `Authorization: Bearer` obrigatório; eventos
  `alert.created` / `alert.updated`; heartbeat
  `LIMEN_SSE_HEARTBEAT_SECONDS`; bridge Redis opcional worker→API.
- Cliente Next: `fetch` + ReadableStream (ADR 0022), reconexão com backoff.
- Spec:
  [`01-justificativa-sse.md`](specs/epic-07-alertas-polish/01-justificativa-sse.md).

### Polish UI — a11y, tema e DLQ (Épico 7 / E7.2)

- Tema dark/light persistente (`limen-theme`) com contraste AA nas telas estrela.
- Toast `aria-live="polite"` para eventos SSE; página `/alertas` navegável por
  teclado.
- Uploads acessíveis (vitals + anexos video/áudio/prescriptions) com
  `aria-describedby`; reveal/remask do Rótulo Sensível com anúncio SR.
- Recharts via `next/dynamic` só em `/casos/[id]` e `/pacientes/[id]` (ADR 0027).
- UI admin `/admin/falhas` (list/redrive/discard); nav e gate só para `admin`.
- Spec:
  [`02-telas-a11y-dlq.md`](specs/epic-07-alertas-polish/02-telas-a11y-dlq.md).

### Gate Lighthouse (Épico 7 / E7.3)

- Pisos absolutos (desktop): Perf ≥90, A11y ≥95, Best Practices ≥90; SEO só
  relatório.
- Regressão: piso efetivo = `max(absoluto, baseline − 2)` vs
  [`docs/perf/baseline/summary.json`](docs/perf/baseline/summary.json).
- Local: `npm run lighthouse:check` (frontend em produção); artefatos em
  `docs/perf/check/` (gitignored) — **não** altera o baseline.
- CI: job **Lighthouse gate** em
  [`.github/workflows/ci.yml`](.github/workflows/ci.yml) com upload dos
  relatórios.
- Índice: [`docs/perf/README.md`](docs/perf/README.md).
- Spec:
  [`03-lighthouse-gate.md`](specs/epic-07-alertas-polish/03-lighthouse-gate.md).

### CI/CD — GHCR + smoke vitais (Épico 8 / E8.1)

- Imagens `ghcr.io/<owner>/limen-backend` e `limen-frontend`: build em todo
  evento CI; **push** com tags `main-<sha>` e `latest` **somente** em push na
  `main` (`GITHUB_TOKEN`, ADR [0028](docs/adr/0028-cicd-actions-ghcr.md)).
- Smoke Compose + Caso só com vitais (`AZURE_ENABLED=false`):
  [`scripts/smoke-caso-vitais.sh`](scripts/smoke-caso-vitais.sh) (local) e job
  **Smoke Caso vitais** no CI (`needs: backend`, push e PR).
- Spec:
  [`01-ghcr-smoke-vitais.md`](specs/epic-08-cicd-entrega/01-ghcr-smoke-vitais.md).

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
e sobe o backend, os workers RQ (`default` e `video`), o reconciler de outbox e
o frontend Next.

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
nem Caso sintético.

### Smoke Caso vitais (Épico 8 / E8.1)

```bash
./scripts/smoke-caso-vitais.sh           # Compose up + Caso vitais até done
./scripts/smoke-caso-vitais.sh --skip-up # stack já no ar
```

Enfileira um Caso só com `data/fixtures/vitals/vitals_medium.csv` (sem
vídeo/áudio/prescrições), autentica com o Operador seed e faz poll até
`status=done`. Espera `AZURE_ENABLED=false` (padrão do `.env.example`). CLI
Python: [`scripts/smoke_caso_vitais.py`](scripts/smoke_caso_vitais.py).
O mesmo fluxo roda no CI (job **Smoke Caso vitais**).

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

Após o worker processar, o GET traz Risco, Alerta (se ≥ MEDIO) e
`justification` (quando o Caso fecha `done`):

```bash
curl -s "http://localhost:8000/cases/$CASE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '{status, risk_level, justification}'
```

### Feed SSE de Alertas

```bash
curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/alerts/stream"
```

Requer Bearer (sem token na query). Comentários `: ping` / `: connected` são
heartbeats; eventos nomeados `alert.created` e `alert.updated` trazem JSON em
`data:`.

### Anexar modalidade vídeo ao Caso

```bash
curl -s -X POST "http://localhost:8000/cases/$CASE_ID/modalities/video" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-video-1" \
  -F "file=@data/fixtures/video/video_physio.avi;type=video/x-msvideo" | jq
```

O job vai para a fila `video` (`worker-video`). Fixture alternativa de cena:
`data/fixtures/video/video_surgery_light.avi`.

### Anexar modalidade áudio ao Caso

```bash
curl -s -X POST "http://localhost:8000/cases/$CASE_ID/modalities/audio" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-audio-1" \
  -F "file=@data/fixtures/audio/audio_speech.wav;type=audio/wav" | jq
```

O job vai para a fila `default`. Após o worker, o `GET /cases/{id}` expõe
`provider` na modalidade `audio` (`local` com `AZURE_ENABLED=false`).

### Anexar modalidade prescriptions ao Caso

```bash
curl -s -X POST "http://localhost:8000/cases/$CASE_ID/modalities/prescriptions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-rx-1" \
  -F "file=@data/fixtures/prescriptions/prescriptions_normal.csv;type=text/csv" | jq
```

O job vai para a fila `default`. Fixtures alternativas: `prescriptions_medium.csv`
e `prescriptions_high.csv`.

### Seed demo multimodal (Épico 8 / E8.2)

Ordem da demo humana: **up → seed → UI**.

```bash
./scripts/start-limen.sh                 # Compose + Operadores seed
./scripts/seed-multimodal-demo.sh        # HTTP: Caso com 4 modalidades
# UI: http://localhost:3000  (login medico / medico_dev_only)
```

O seed HTTP usa as `Idempotency-Key` fixas (`limen-demo-multimodal-*-v1`),
anexa `vitals` + `video` + `audio` + `prescriptions` e é **idempotente**
(reexecutar não duplica o Caso). Espera `AZURE_ENABLED=false`.

Alternativa in-memory (sem Compose, só contrato/TDD):

```bash
cd backend && uv run python ../scripts/seed_multimodal_demo.py --memory
```

Não substitui o smoke de Caso vitais (`./scripts/smoke-caso-vitais.sh`).

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
| `LIMEN_SSE_HEARTBEAT_SECONDS` | Intervalo de ping SSE de Alertas (padrão `15`) |
| `LIMEN_TIMEOUT_VITALS_SECONDS` | Timeout job vitais (padrão `30`) |
| `LIMEN_TIMEOUT_AUDIO_SECONDS` | Timeout job áudio (padrão `90`) |
| `LIMEN_TIMEOUT_VIDEO_SECONDS` | Timeout job vídeo (padrão `180`) |
| `LIMEN_TIMEOUT_PRESCRIPTIONS_SECONDS` | Timeout job prescriptions (padrão `30`) |
| `LIMEN_RETRY_MAX_ATTEMPTS` | Máx. tentativas para erro transitório (padrão `3`) |
| `LIMEN_RETRY_BASE_DELAY_SECONDS` | Base do backoff exponencial (padrão `1`) |
| `AZURE_ENABLED` | Habilita caminho Azure Speech (padrão `false`; CI/demo usa local/cache) |
| `LIMEN_AZURE_CB_FAILURE_THRESHOLD` | Falhas consecutivas para abrir o CB (padrão `3`) |
| `LIMEN_AZURE_CB_OPEN_SECONDS` | Segundos com CB aberto forçando `local` (padrão `300`) |
| `LIMEN_AZURE_CB_FORCE_OPEN` | Força CB aberto no stub (`true`/`1`) |
| `LIMEN_POSE_BACKEND` | Análise Postural: `synthetic` (padrão) ou `mediapipe` |
| `LIMEN_YOLO_BACKEND` | Detecção em Cena: `synthetic` (padrão) ou `ultralytics` |
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
e PRs: backend (`uv sync`, compileall, pytest), job **Lighthouse gate**
(build/start do frontend + `npm run lighthouse:check` vs
[`docs/perf/baseline/`](docs/perf/baseline/), artefatos em `docs/perf/check/`)
e job **Docker images (GHCR)** — build de `limen-backend` / `limen-frontend` em
todo evento; **push** para `ghcr.io/<owner>/…` com tags `main-<sha>` e `latest`
**somente** em push na `main` (`GITHUB_TOKEN`, ADR
[0028](docs/adr/0028-cicd-actions-ghcr.md)); e job **Smoke Caso vitais**
(`needs: backend`, Compose + `./scripts/smoke-caso-vitais.sh`,
`AZURE_ENABLED=false`) em push e PR — localmente o mesmo script.

## Documentação

| Documento | Conteúdo |
| --------- | -------- |
| [`CONTEXT.md`](CONTEXT.md) | Linguagem ubíqua (Paciente, Caso, Risco, …) |
| [`docs/README.md`](docs/README.md) | Índice de ADRs e specs |
| [`docs/architecture.md`](docs/architecture.md) | Diagramas Mermaid da arquitetura (Compose, filas, fusão, …) |
| [`specs/epic-01-foundation/`](specs/epic-01-foundation/) | Contrato Compose/health |
| [`specs/epic-02-identity/`](specs/epic-02-identity/) | Contratos auth e Paciente |
| [`specs/epic-03-caso-fila/`](specs/epic-03-caso-fila/) | Vitais, outbox/RQ, Caso → Risco/Alerta |
| [`specs/epic-04-shell-frontend/`](specs/epic-04-shell-frontend/) | Shell Next (scaffold → login → Pacientes) |
| [`specs/epic-05-resiliencia/`](specs/epic-05-resiliencia/) | Falha parcial, filas, DLQ/retries |
| [`specs/epic-06-modalidades/`](specs/epic-06-modalidades/) | Vídeo (E6.1); áudio Azure F0 (E6.2); prescriptions + seed (E6.3) |
| [`specs/epic-07-alertas-polish/`](specs/epic-07-alertas-polish/) | Justificativa + SSE (E7.1); a11y/DLQ (E7.2); Lighthouse gate (E7.3) — concluído |
| [`specs/epic-08-cicd-entrega/`](specs/epic-08-cicd-entrega/) | GHCR + smoke vitais (E8.1) — concluído; seed/notebooks/relatório (E8.2) — spec |
| [`frontend/`](frontend/) | App Next.js (Épico 4 + Épico 7) |
| [`.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md`](.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md) | Plano incremental dos épicos |

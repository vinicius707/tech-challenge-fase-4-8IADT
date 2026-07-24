# Documentação do Limen

Índice da documentação de arquitetura e contratos SDD do protótipo acadêmico
Limen (FIAP 8IADT — Fase 4).

> O Limen não é um dispositivo médico.

- Glossário: [`../CONTEXT.md`](../CONTEXT.md)
- README operacional: [`../README.md`](../README.md)
- **Arquitetura (diagramas Mermaid):** [`architecture.md`](architecture.md)
- Plano incremental:
  [`../.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md`](../.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md)

## Arquitetura

Diagramas canônicos da stack pós-Épico 6 (Compose, Caso multimodal, filas,
fusão de Risco, Provedor de Áudio, Prescrições e mapa de épicos):

→ [`architecture.md`](architecture.md)

## Specs (SDD)

Contratos Given/When/Then escritos **antes** da implementação TDD.

| Épico | Spec | Status |
| ----- | ---- | ------ |
| 1 Fundação | [`../specs/epic-01-foundation/01-compose-health.md`](../specs/epic-01-foundation/01-compose-health.md) | Concluída |
| 2 Identidade | [`../specs/epic-02-identity/01-auth-login.md`](../specs/epic-02-identity/01-auth-login.md) | Concluída |
| 2 Identidade | [`../specs/epic-02-identity/02-paciente-privacidade.md`](../specs/epic-02-identity/02-paciente-privacidade.md) | Concluída |
| 3 Caso + fila | [`../specs/epic-03-caso-fila/01-datasets-vitais.md`](../specs/epic-03-caso-fila/01-datasets-vitais.md) | Concluída |
| 3 Caso + fila | [`../specs/epic-03-caso-fila/02-outbox-rq.md`](../specs/epic-03-caso-fila/02-outbox-rq.md) | Concluída |
| 3 Caso + fila | [`../specs/epic-03-caso-fila/03-caso-vitais-risco.md`](../specs/epic-03-caso-fila/03-caso-vitais-risco.md) | Concluída |
| 4 Shell Frontend | [`../specs/epic-04-shell-frontend/01-scaffold-auth.md`](../specs/epic-04-shell-frontend/01-scaffold-auth.md) | Concluída |
| 4 Shell Frontend | [`../specs/epic-04-shell-frontend/02-pacientes-caso-ui.md`](../specs/epic-04-shell-frontend/02-pacientes-caso-ui.md) | Concluída |
| 4 Shell Frontend | [`../specs/epic-04-shell-frontend/03-lighthouse-baseline.md`](../specs/epic-04-shell-frontend/03-lighthouse-baseline.md) | Concluída |
| 4 Shell Frontend | [`../specs/epic-04-shell-frontend/04-fechamento-docs.md`](../specs/epic-04-shell-frontend/04-fechamento-docs.md) | Concluída |
| 5 Resiliência | [`../specs/epic-05-resiliencia/01-falha-parcial-reprocess.md`](../specs/epic-05-resiliencia/01-falha-parcial-reprocess.md) | Concluída |
| 5 Resiliência | [`../specs/epic-05-resiliencia/02-filas-dlq-retries.md`](../specs/epic-05-resiliencia/02-filas-dlq-retries.md) | Concluída |
| 6 Modalidades | [`../specs/epic-06-modalidades/01-video-pose-yolo.md`](../specs/epic-06-modalidades/01-video-pose-yolo.md) | Concluída (E6.1 seam); real → Épico 11 |
| 6 Modalidades | [`../specs/epic-06-modalidades/02-audio-azure.md`](../specs/epic-06-modalidades/02-audio-azure.md) | Concluída (E6.2 seam); real → Épico 10 |
| 6 Modalidades | [`../specs/epic-06-modalidades/03-prescricoes-seed.md`](../specs/epic-06-modalidades/03-prescricoes-seed.md) | Concluída (E6.3) |
| 7 Alertas + polish | [`../specs/epic-07-alertas-polish/01-justificativa-sse.md`](../specs/epic-07-alertas-polish/01-justificativa-sse.md) | Concluída (E7.1) |
| 7 Alertas + polish | [`../specs/epic-07-alertas-polish/02-telas-a11y-dlq.md`](../specs/epic-07-alertas-polish/02-telas-a11y-dlq.md) | Concluída (E7.2) |
| 7 Alertas + polish | [`../specs/epic-07-alertas-polish/03-lighthouse-gate.md`](../specs/epic-07-alertas-polish/03-lighthouse-gate.md) | Concluída (E7.3) |
| 8 CI/CD e entrega | [`../specs/epic-08-cicd-entrega/01-ghcr-smoke-vitais.md`](../specs/epic-08-cicd-entrega/01-ghcr-smoke-vitais.md) | Concluída (E8.1) |
| 8 CI/CD e entrega | [`../specs/epic-08-cicd-entrega/02-seed-notebooks-relatorio.md`](../specs/epic-08-cicd-entrega/02-seed-notebooks-relatorio.md) | Concluída (E8.2) |
| 9 Vitais ML | [`../specs/epic-09-vitais-ml/00-baseline-atual.md`](../specs/epic-09-vitais-ml/00-baseline-atual.md) | Baseline (só docs) |
| 9 Vitais ML | [`../specs/epic-09-vitais-ml/01-etl-datasets-vitais.md`](../specs/epic-09-vitais-ml/01-etl-datasets-vitais.md) | Concluída (E9.1 ETL) |
| 9 Vitais ML | [`../specs/epic-09-vitais-ml/02-isolation-forest-runtime.md`](../specs/epic-09-vitais-ml/02-isolation-forest-runtime.md) | Concluída (E9.2 IF runtime) |
| 9 Vitais ML | [`../specs/epic-09-vitais-ml/03-autoencoder-notebook.md`](../specs/epic-09-vitais-ml/03-autoencoder-notebook.md) | Concluída (E9.3 AE notebook) |
| 9 Vitais ML | [`../specs/epic-09-vitais-ml/04-comparacao-relatorio-roteiro.md`](../specs/epic-09-vitais-ml/04-comparacao-relatorio-roteiro.md) | Spec (E9.4) — pendente impl. |
| 10 Azure áudio real | [`../specs/epic-10-azure-audio-real/01-speech-language-evidencia.md`](../specs/epic-10-azure-audio-real/01-speech-language-evidencia.md) | Concluída (E10) |
| 11 Vídeo real (YOLO + Pose) | [`../specs/epic-11-yolo-video-real/01-ultralytics-mediapipe-evidencia.md`](../specs/epic-11-yolo-video-real/01-ultralytics-mediapipe-evidencia.md) | Concluída (E11) |

> Fila de implementação das frentes de IA real: **Épico 10 (feito) → Épico 11
> (feito) → Épico 9**. O Épico 9 tem SDD pronto; **não está encerrado** (código
> não iniciado). Épicos 6.x permanecem Concluída (seam/sintético).

## ADRs

Arquivos em [`adr/`](adr/). Numeração estável; emendas pontuais ficam no próprio
arquivo quando o plano supersede uma decisão anterior.

### Privacidade, auth e segurança

| ADR | Tema |
| --- | ---- |
| [0001](adr/0001-privacidade-paciente.md) | Paciente pseudônimo + Rótulo Sensível |
| [0004](adr/0004-auth-jwt-papeis.md) | JWT e papéis `medico` / `admin` |
| [0005](adr/0005-chave-pii-ambiente.md) | `PII_ENCRYPTION_KEY` em ambiente |
| [0006](adr/0006-endurecimento-seguranca.md) | bcrypt, rate limit, auditoria (emenda Épico 2: refresh) |
| [0021](adr/0021-auth-api-papeis.md) | Rotas públicas vs Bearer; worker fora do HTTP |

### Persistência e infraestrutura

| ADR | Tema |
| --- | ---- |
| [0009](adr/0009-postgres-redis.md) | Postgres (domínio) + Redis (fila) |
| [0011](adr/0011-artefatos-minio.md) | Artefatos no MinIO |
| [0012](adr/0012-nome-limen.md) | Nome do produto |
| [0016](adr/0016-outbox-leve.md) | Outbox leve |
| [0018](adr/0018-idempotencia.md) | Idempotência |
| [0019](adr/0019-observabilidade.md) | Healthchecks e observabilidade |
| [0028](adr/0028-cicd-actions-ghcr.md) | CI/CD Actions + GHCR |

### Domínio clínico / fila

| ADR | Tema |
| --- | ---- |
| [0002](adr/0002-fila-redis-worker.md) | Fila Redis + RQ |
| [0003](adr/0003-painel-dlq-redrive.md) | Painel DLQ / redrive |
| [0007](adr/0007-escopo-video-fisio-cirurgia-leve.md) | Escopo de vídeo |
| [0008](adr/0008-vitais-sinteticos.md) | Vitais sintéticos (emenda Épico 9 → ADR 0029) |
| [0010](adr/0010-prescricoes-regras-historico.md) | Prescrições |
| [0029](adr/0029-vitais-ml-hibrido.md) | Vitais ML: IF runtime + AE PyTorch evidência |
| [0013](adr/0013-falha-parcial-reprocessamento.md) | Falha parcial |
| [0014](adr/0014-alertas-versionados.md) | Alertas versionados |
| [0015](adr/0015-retry-circuit-breaker-azure.md) | Retry / CB Azure |
| [0017](adr/0017-timeouts-por-modalidade.md) | Timeouts por modalidade |
| [0020](adr/0020-filas-separadas-video.md) | Filas `video` / `default` |
| [0031](adr/0031-audio-nlp-modelagem.md) | Áudio NLP: Termo Crítico / Sentimento como Anomalias |

### IA real e evidência

| ADR | Tema |
| --- | ---- |
| [0030](adr/0030-ia-real-opt-in-evidencia.md) | IA real opt-in; CI sintético; evidência commitada |

### Frontend (épicos seguintes)

| ADR | Tema |
| --- | ---- |
| [0022](adr/0022-sse-fetch-stream.md) | SSE com `fetch` + Bearer |
| [0023](adr/0023-frontend-nextjs.md) | Next.js |
| [0024](adr/0024-ui-tailwind-shadcn.md) | Tailwind + shadcn |
| [0025](adr/0025-estado-query-zustand.md) | Estado / Query / Zustand |
| [0026](adr/0026-rotas-frontend.md) | Mapa de rotas |
| [0027](adr/0027-graficos-recharts-lazy.md) | Recharts lazy |

## Performance

- Índice: [`perf/README.md`](perf/README.md) — gate absoluto + regressão (tolerância
  2; rotas `/login`, `/pacientes`)
- Baseline versionada: [`perf/baseline/`](perf/baseline/)
- Script / CI: `npm run lighthouse:check` em `frontend/` (job `Lighthouse gate`)

## Frontend (operacional)

- Índice: [`frontend/README.md`](frontend/README.md)
- [Guia de uso com prints](frontend/guia-de-uso.md)
- [Troubleshooting](frontend/troubleshooting.md)
- Script de start da stack: [`../scripts/start-limen.sh`](../scripts/start-limen.sh)

## Progresso por épico

| Épico | Tema | Status |
| ----- | ---- | ------ |
| 1 | Fundação | Concluído |
| 2 | Identidade e privacidade | Concluído |
| 3 | Núcleo Caso + fila | Concluído |
| 4 | Shell Frontend | Concluído |
| 5 | Resiliência | Concluído |
| 6 | Modalidades PDF | Concluído (E6.1 vídeo; E6.2 áudio; E6.3 prescrições + seed) |
| 7 | Alertas + polish UI | Concluído (E7.1–E7.3) |
| 8 | CI/CD e entrega | Concluído (E8.1–E8.2) |
| 9 | Vitais ML (portfólio) | Specs + ADR 0029; **impl. não iniciada** (próximo na fila) |
| 10 | Azure áudio real | Concluído (E10) — Speech + Language opt-in + evidência |
| 11 | Vídeo real (YOLO + Pose) | Concluído (E11) — Ultralytics + MediaPipe + evidência |

## Entrega acadêmica (E8.2)

- Relatório Fase 4: [`relatorio-fase4.md`](relatorio-fase4.md) (capítulo de datasets)
- Roteiro de vídeo: [`demo/roteiro-video.md`](demo/roteiro-video.md)
- Notebooks: [`../notebooks/`](../notebooks/)
- Seed Compose: [`../scripts/seed-multimodal-demo.sh`](../scripts/seed-multimodal-demo.sh)
- Spec: [`../specs/epic-08-cicd-entrega/02-seed-notebooks-relatorio.md`](../specs/epic-08-cicd-entrega/02-seed-notebooks-relatorio.md)

## CI/CD (E8.1)

- Workflow: [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) —
  backend, Lighthouse, imagens GHCR, smoke Caso vitais
- Imagens: `ghcr.io/<owner>/limen-backend` e `limen-frontend` (`main-<sha>`,
  `latest` só em push na `main`)
- Smoke local/CI: [`../scripts/smoke-caso-vitais.sh`](../scripts/smoke-caso-vitais.sh)
- ADR: [0028](adr/0028-cicd-actions-ghcr.md)
- Spec: [`../specs/epic-08-cicd-entrega/01-ghcr-smoke-vitais.md`](../specs/epic-08-cicd-entrega/01-ghcr-smoke-vitais.md)

## Azure áudio real (E10)

- Spec:
  [`../specs/epic-10-azure-audio-real/01-speech-language-evidencia.md`](../specs/epic-10-azure-audio-real/01-speech-language-evidencia.md)
- ADRs: [0030](adr/0030-ia-real-opt-in-evidencia.md),
  [0031](adr/0031-audio-nlp-modelagem.md) (+ [0015](adr/0015-retry-circuit-breaker-azure.md))
- Evidência: [`../data/evidencia/audio/`](../data/evidencia/audio/) via
  `./scripts/gerar-evidencia-audio.sh`
- Env: `AZURE_ENABLED` + `AZURE_SPEECH_*` + `AZURE_LANGUAGE_*` no `.env.example`

## Vídeo real YOLO + MediaPipe (E11)

- Spec:
  [`../specs/epic-11-yolo-video-real/01-ultralytics-mediapipe-evidencia.md`](../specs/epic-11-yolo-video-real/01-ultralytics-mediapipe-evidencia.md)
- ADRs: [0030](adr/0030-ia-real-opt-in-evidencia.md),
  [0007](adr/0007-escopo-video-fisio-cirurgia-leve.md)
- Evidência: [`../data/evidencia/video/`](../data/evidencia/video/) via
  `./scripts/gerar-evidencia-video.sh`
- Override Compose: [`../docker-compose.video-real.yml`](../docker-compose.video-real.yml)
- Env: `LIMEN_YOLO_BACKEND` / `LIMEN_POSE_BACKEND` no `.env.example`

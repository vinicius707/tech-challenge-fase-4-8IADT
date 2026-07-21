# Documentação do Limen

Índice da documentação de arquitetura e contratos SDD do protótipo acadêmico
Limen (FIAP 8IADT — Fase 4).

> O Limen não é um dispositivo médico.

- Glossário: [`../CONTEXT.md`](../CONTEXT.md)
- README operacional: [`../README.md`](../README.md)
- Plano incremental:
  [`../.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md`](../.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md)

## Specs (SDD)

Contratos Given/When/Then escritos **antes** da implementação TDD.

| Épico | Spec | Status |
| ----- | ---- | ------ |
| 1 Fundação | [`../specs/epic-01-foundation/01-compose-health.md`](../specs/epic-01-foundation/01-compose-health.md) | Concluída |
| 2 Identidade | [`../specs/epic-02-identity/01-auth-login.md`](../specs/epic-02-identity/01-auth-login.md) | Concluída |
| 2 Identidade | [`../specs/epic-02-identity/02-paciente-privacidade.md`](../specs/epic-02-identity/02-paciente-privacidade.md) | Concluída |

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

### Domínio clínico / fila (épicos seguintes)

| ADR | Tema |
| --- | ---- |
| [0002](adr/0002-fila-redis-worker.md) | Fila Redis + RQ |
| [0003](adr/0003-painel-dlq-redrive.md) | Painel DLQ / redrive |
| [0007](adr/0007-escopo-video-fisio-cirurgia-leve.md) | Escopo de vídeo |
| [0008](adr/0008-vitais-sinteticos.md) | Vitais sintéticos |
| [0010](adr/0010-prescricoes-regras-historico.md) | Prescrições |
| [0013](adr/0013-falha-parcial-reprocessamento.md) | Falha parcial |
| [0014](adr/0014-alertas-versionados.md) | Alertas versionados |
| [0015](adr/0015-retry-circuit-breaker-azure.md) | Retry / CB Azure |
| [0017](adr/0017-timeouts-por-modalidade.md) | Timeouts por modalidade |
| [0020](adr/0020-filas-separadas-video.md) | Filas `video` / `default` |

### Frontend (épicos seguintes)

| ADR | Tema |
| --- | ---- |
| [0022](adr/0022-sse-fetch-stream.md) | SSE com `fetch` + Bearer |
| [0023](adr/0023-frontend-nextjs.md) | Next.js |
| [0024](adr/0024-ui-tailwind-shadcn.md) | Tailwind + shadcn |
| [0025](adr/0025-estado-query-zustand.md) | Estado / Query / Zustand |
| [0026](adr/0026-rotas-frontend.md) | Mapa de rotas |
| [0027](adr/0027-graficos-recharts-lazy.md) | Recharts lazy |

## Progresso por épico

| Épico | Tema | Status |
| ----- | ---- | ------ |
| 1 | Fundação | Concluído |
| 2 | Identidade e privacidade | Concluído |
| 3 | Núcleo Caso + fila | Próximo |
| 4–8 | Shell UI, resiliência, modalidades, Alertas, CI/CD | Pendente |

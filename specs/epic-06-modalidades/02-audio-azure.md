# Modalidades — Áudio (Azure F0 + fallback)

## Objetivo

Entregar a modalidade `audio`: sample ≤60s, Speech Azure F0 com cache,
fallback local, circuit breaker (Épico 5) e badge de Provedor de Áudio
(`azure` \| `local` \| `cache`) no Caso.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** — spec fina a ser detalhada/aprovada no **início da etapa E6.2**
(após DoD de E6.1). Este arquivo é placeholder de índice do épico.

## Escopo (rascunho do plano)

- Fixture AudioSet / Medical Speech ≤60s em `data/fixtures/audio/`.
- Cliente Azure F0 + cache; fallback local; CB já stubado em `app/azure/`.
- Badge `provider` na resposta do Caso / modalidade áudio.
- Fila `default` (ADR 0020).

Ficam fora (até a spec fina): UI polish; SSE; Exactly-once.

## ADRs aplicáveis (previstos)

- [ADR 0015 — Retry / CB Azure](../../docs/adr/0015-retry-circuit-breaker-azure.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0017 — Timeouts](../../docs/adr/0017-timeouts-por-modalidade.md)
- [ADR 0020 — Filas](../../docs/adr/0020-filas-separadas-video.md)

# Modalidades — Prescrições + seed multimodal

## Objetivo

Entregar a modalidade `prescriptions` com regras determinísticas + desvio
longitudinal (histórico do Paciente), CSV sintético seed e Casos demo
multimodais (vitais + vídeo + áudio + prescrições).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** — spec fina a ser detalhada/aprovada no **início da etapa E6.3**
(após DoD de E6.2). Este arquivo é placeholder de índice do épico.

## Escopo (rascunho do plano)

- Regras de dose/intervalo/medicamento inesperado (ADR 0010).
- Desvio vs. Casos anteriores do mesmo Paciente quando houver histórico.
- Fixtures CSV em `data/fixtures/prescriptions/`.
- Seed demo com Casos multimodais.

Ficam fora (até a spec fina): UI de prescrições avançada; integração farmácia.

## ADRs aplicáveis (previstos)

- [ADR 0010 — Prescrições regras + histórico](../../docs/adr/0010-prescricoes-regras-historico.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0013 — Falha parcial](../../docs/adr/0013-falha-parcial-reprocessamento.md)
- [ADR 0001 — Privacidade](../../docs/adr/0001-privacidade-paciente.md)

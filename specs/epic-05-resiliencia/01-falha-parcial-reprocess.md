# Resiliência — Falha parcial, reprocessamento e Alerta v2

## Objetivo

Definir o comportamento de resiliência **por modalidade** no Caso: falha
parcial com Caso `done`, reprocessamento seletivo das modalidades `failed`,
refundição do Risco e emissão de Alerta v2 quando o nível cruzar limiar —
sobre store compartilhado entre API e worker (Compose).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 21 de julho de 2026** (T5.0–T5.4: specs, store compartilhado,
falha parcial, reprocess seletivo, Alerta v2). Filas/DLQ ficam na spec `02`.

## Escopo

- Persistência de Caso / modalidades / Artefatos (metadados) / outbox em
  **Postgres** (ou store equivalente) **compartilhado** entre processo API e
  worker RQ — pré-requisito para falha parcial e redrive no Compose.
- Status independente por modalidade (`pending` \| `processing` \| `done` \|
  `failed` \| `skipped`).
- Caso pode ficar `done` com subconjunto de modalidades bem-sucedidas (falha
  parcial); modalidades `failed` não entram na fusão (pesos renormalizados
  quando houver ≥1 modalidade `done`).
- Endpoint (ou operação autenticada) de **reprocessamento seletivo**: enfileira
  jobs só para modalidades `failed`, reutiliza Artefatos no MinIO, refundiciona
  o Risco ao concluir.
- Alerta versionado: se o reprocessamento alterar o `risk_level` (cruzamento
  de limiar), persiste **nova versão** append-only (ex.: v2) do Alerta; versões
  anteriores permanecem. Sem SSE neste épico (feed fica no Épico 7).
- Testes TDD cobrindo falha forçada de uma modalidade e Caso parcial `done`.

Ficam fora desta etapa: filas `video`/`default` separadas e DLQ admin (spec
`02`); UI de reprocess/DLQ; Justificativa rica por template; SSE; modalidades
`video`/`audio`/`prescriptions` reais (Épico 6); circuit breaker Azure real
(stub na spec `02`); dark mode / AA.

## ADRs aplicáveis

- [ADR 0013 — Falha parcial / reprocess](../../docs/adr/0013-falha-parcial-reprocessamento.md)
- [ADR 0014 — Alertas versionados](../../docs/adr/0014-alertas-versionados.md)
- [ADR 0016 — Outbox leve](../../docs/adr/0016-outbox-leve.md)
- [ADR 0018 — Idempotência](../../docs/adr/0018-idempotencia.md)
- [ADR 0009 — Postgres + Redis](../../docs/adr/0009-postgres-redis.md):
  store de domínio no Postgres

## Contratos HTTP (mínimos)

Autenticação Bearer; papéis `medico` e `admin` (reprocess sem ser exclusivo de
admin nesta etapa — DLQ admin é a spec `02`).

### `POST /cases/{case_id}/reprocess`

Body opcional: lista de modalidades a reprocessar; default = todas `failed`.

Sucesso: `202 Accepted` (ou `200`) com Caso atualizado / jobs enfileirados.
Caso inexistente → `404`. Sem modalidades `failed` elegíveis → `409` ou `400`
documentado.

### `GET /cases/{case_id}`

Já existente; deve expor status por modalidade, `risk_*` e `alerts` com
`version`.

## Cenários de aceitação

### Cenário 1 — Falha parcial → Caso `done`

**Dado** um Caso com ≥1 modalidade `vitals` que conclui com sucesso e um
mecanismo de falha forçada em outra modalidade (ou stub de segunda modalidade
no teste)  
**Quando** o worker processar  
**Então** a modalidade com falha fica `failed`  
**E** o Caso pode ficar `done` com Risco calculado só sobre modalidades `done`.

### Cenário 2 — Reprocess seletivo

**Dado** Caso com modalidade `failed` e Artefato ainda no MinIO  
**Quando** chamar `POST /cases/{id}/reprocess`  
**Então** apenas a(s) modalidade(s) `failed` são enfileiradas  
**E** ao concluir, o Risco é refundido.

### Cenário 3 — Alerta v2

**Dado** Caso com Alerta v1 (`MEDIO` ou `ALTO`)  
**Quando** o reprocessamento alterar o `risk_level`  
**Então** deve existir Alerta com `version` incrementada  
**E** a versão anterior permanece consultável no GET do Caso.

### Cenário 4 — Auth

**Dado** ausência de sessão  
**Quando** chamar reprocess  
**Então** `401`.

## Critérios de pronto (DoD desta spec)

- [x] Store compartilhado API↔worker (Caso/outbox) validado no Compose.
- [x] Falha parcial + Caso `done` cobertos por TDD.
- [x] Reprocess seletivo + refundição cobertos por TDD.
- [x] Alerta v2 append-only quando o nível muda.
- [x] Sem SSE; sem UI de DLQ.

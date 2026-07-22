# Resiliência — Filas, retries, timeouts e DLQ admin

## Objetivo

Definir a resiliência operacional da fila: filas RQ `default` e `video`,
retries classificados, timeouts por modalidade, dead-letter (Falhas de
Processamento) com API admin de listagem/redrive/discard + auditoria, e stub
de circuit breaker (Azure) — com `403` para papel `medico` nas rotas admin.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** (T5.5 filas; falta T5.6–T5.8).

## Escopo

- Filas RQ distintas: `default` (vitais, áudio, prescricões, fusão/refundição)
  e `video` (jobs pesados). Compose: worker(s) consumindo cada conjunto (ADR
  0020). Nesta etapa, jobs `vitals`/reprocess continuam em `default`; a fila
  `video` existe e é exercitada por job stub ou fixture mínima (processamento
  real de vídeo = Épico 6).
- Classificação de erros: **transitórios** → retry com backoff no RQ;
  **permanentes** → modalidade `failed` e/ou registro na DLQ após esgotar
  política.
- Timeouts configuráveis por modalidade (ADR 0017); estouro → modalidade
  `failed` (demais seguem — falha parcial da spec `01`).
- **Falhas de Processamento (DLQ)**: após max retries, expor na API admin:
  listar, inspecionar (mensagem/resumo), `redrive` (reenqueue) e `discard`,
  com Registro de Auditoria. Não confundir com Alertas clínicos.
- Rotas sob prefixo `/admin/failures` (ou equivalente); papel `admin` OK;
  `medico` → `403`.
- Circuit breaker Azure: **stub** (estado aberto/fechado configurável ou
  contador in-memory) pronto para o Épico 6; sem chamada Azure real aqui.

Ficam fora desta etapa: UI Next de `/admin/falhas` (Épico 7); processamento
real de vídeo/áudio/Azure F0 (Épico 6); SSE; Exactly-once formal; Prometheus.

## ADRs aplicáveis

- [ADR 0002 — RQ](../../docs/adr/0002-fila-redis-worker.md)
- [ADR 0003 — Painel DLQ / redrive](../../docs/adr/0003-painel-dlq-redrive.md)
- [ADR 0004 / 0021 — Papéis](../../docs/adr/0004-auth-jwt-papeis.md)
- [ADR 0015 — Retries + CB Azure](../../docs/adr/0015-retry-circuit-breaker-azure.md)
- [ADR 0017 — Timeouts](../../docs/adr/0017-timeouts-por-modalidade.md)
- [ADR 0020 — Filas `video` / `default`](../../docs/adr/0020-filas-separadas-video.md)
- [ADR 0006 — Auditoria](../../docs/adr/0006-endurecimento-seguranca.md)

## Contratos HTTP (mínimos)

### `GET /admin/failures`

Lista falhas (paginação mínima). Auth: `admin`. `medico` → `403`.

### `GET /admin/failures/{id}`

Detalhe (exceção resumida, `case_id`, modalidade, tentativas).

### `POST /admin/failures/{id}/redrive`

Reenfileira o job (outbox/RQ) de forma idempotente com o worker. Auditoria.

### `POST /admin/failures/{id}/discard`

Descarta a falha (marca descartada; não reprocessa). Auditoria.

## Cenários de aceitação

### Cenário 1 — Falha forçada → DLQ → redrive

**Dado** um job que esgota retries com erro permanente (ou força de teste)  
**Quando** consultar `GET /admin/failures` como `admin`  
**Então** a falha aparece  
**E** `POST …/redrive` reenfileira  
**E** o worker pode concluir (ou falhar de novo de forma controlada).

### Cenário 2 — `medico` proibido

**Dado** Operador `medico`  
**Quando** acessar qualquer rota `/admin/failures*`  
**Então** `403`.

### Cenário 3 — Timeout de modalidade

**Dado** timeout configurado curto no teste  
**Quando** o job estourar  
**Então** a modalidade fica `failed`  
**E** as demais podem seguir (falha parcial).

### Cenário 4 — Filas

**Dado** Compose com workers `default` e `video`  
**Quando** enfileirar job de tipo `video` (stub)  
**Então** ele é consumido pela fila `video`  
**E** jobs `vitals` permanecem em `default`.

### Cenário 5 — CB stub

**Dado** circuit breaker em estado aberto (stub)  
**Quando** um caminho “Azure” for consultado no código  
**Então** o stub força fallback/local sem chamar rede externa.

## Critérios de pronto (DoD desta spec)

- [x] Filas `default` + `video` no Compose/RQ.
- [ ] Retries classificados + timeouts exercitados em TDD.
- [ ] API DLQ list/redrive/discard + audit; `403` para `medico`.
- [ ] CB Azure stub (sem Azure real).
- [ ] DoD do épico: falha forçada → DLQ → redrive demonstrável.

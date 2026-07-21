# Núcleo Caso + fila — Outbox Postgres → RQ

## Objetivo

Definir o pipeline mínimo de enfileiramento do Limen: jobs gravados primeiro no
PostgreSQL (outbox), despachados para Redis Queue na fila `default`, consumidos
por um worker no Compose, com reconciler básico quando o Redis estiver
indisponível no momento do enqueue.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Parcial — T3.3:** migração `outbox_jobs` + dispatcher/enqueue cobertos por TDD
(cenários 1–3). Worker Compose e reconciler: **T3.4**.

## Escopo

- Tabela de outbox/jobs no PostgreSQL como fonte da verdade do trabalho a fazer.
- Enfileiramento na fila RQ nomeada `default`.
- Processo worker no Docker Compose consumindo `default`.
- Reconciler básico: periodicamente (ou sob comando) promove registros
  `pending`/`enqueue_failed` do outbox para o RQ quando o Redis estiver saudável.
- Contrato mínimo de payload do job (referência a Caso / modalidade) suficiente
  para o Épico 3 processar vitais.
- Observabilidade mínima: status do registro no outbox consultável em testes;
  falha de Redis não apaga o outbox.

Ficam fora desta etapa: fila `video` separada; DLQ / painel admin / redrive;
retries classificados e timeouts por modalidade (Épico 5); circuit breaker
Azure; SSE; API pública de “listar outbox”; Exactly-once formal além do
comportamento at-least-once com idempotência no worker (spec `03`).

## ADRs aplicáveis

- [ADR 0002 — Fila Redis + RQ](../../docs/adr/0002-fila-redis-worker.md):
  ciclo de vida de processamento via RQ + worker no Compose.
- [ADR 0016 — Outbox leve](../../docs/adr/0016-outbox-leve.md):
  Postgres primeiro; RQ como dispatcher; reconciler se Redis cair.
- [ADR 0009 — PostgreSQL + Redis](../../docs/adr/0009-postgres-redis.md):
  estado de domínio no Postgres; Redis como broker.
- [ADR 0020 — Filas separadas vídeo](../../docs/adr/0020-filas-separadas-video.md):
  nesta etapa só existe `default`; `video` fica para épicos seguintes.

## Modelo de outbox

**Registro de outbox (nome de tabela a cargo da implementação, ex.: `outbox_jobs`)**

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `id` | UUID | PK |
| `aggregate_type` | string | ex.: `case` |
| `aggregate_id` | UUID | id do Caso |
| `job_type` | string | ex.: `process_modality` |
| `payload` | JSON | mínimo: `case_id`, `modality` (`vitals`) |
| `status` | string | `pending` \| `enqueued` \| `processed` \| `enqueue_failed` |
| `rq_job_id` | string nullable | id no RQ após enqueue bem-sucedido |
| `attempts` | int | tentativas de enqueue/reconcile |
| `last_error` | text nullable | sem stack interna em APIs públicas |
| `created_at`, `updated_at` | timestamptz | |

Regras:

1. Toda transição que exige processamento assíncrono **grava o outbox na mesma
   transação** do estado de domínio (quando aplicável) antes de falar com Redis.
2. Se o enqueue no RQ falhar, o registro permanece `pending` ou
   `enqueue_failed` e o reconciler tenta de novo.
3. Postgres indisponível → API responde `503` (já alinhado ao health); não se
   inventa fila só-em-memória.
4. Worker, ao concluir com sucesso o trabalho da spec `03`, marca o outbox como
   `processed` (ou equivalente) de forma idempotente.

## RQ e Compose

- Fila: `default` apenas.
- Serviço `worker` (ou nome equivalente) no `docker-compose.yml`, apontando ao
  mesmo Redis/Postgres/MinIO do backend.
- Variáveis documentadas em `.env.example` (ex.: `REDIS_URL`, nome da fila se
  configurável).

## Reconciler

- Processo ou loop leve (no worker ou serviço dedicado mínimo) que:
  - seleciona registros elegíveis (`pending` / `enqueue_failed`);
  - tenta `enqueue` no RQ;
  - atualiza `status`, `rq_job_id`, `attempts`, `last_error`.
- Não precisa de UI; coberto por testes TDD.

## Cenários de aceitação

### Cenário 1 — Outbox antes do RQ

**Dado** uma operação de domínio que exige processamento (ex.: criação de Caso
com vitais na spec `03`)  
**Quando** a transação de criação concluir com sucesso  
**Então** deve existir um registro de outbox com `status` `pending` ou já
`enqueued`  
**E** o payload deve referenciar o `case_id` e a modalidade `vitals`.

### Cenário 2 — Enqueue bem-sucedido

**Dado** Redis disponível e um registro `pending`  
**Quando** o dispatcher/reconciler enfileirar o job  
**Então** o status deve passar a `enqueued`  
**E** `rq_job_id` deve ser preenchido  
**E** o worker deve poder consumir o job da fila `default`.

### Cenário 3 — Redis indisponível no enqueue

**Dado** Redis indisponível no momento do enqueue  
**Quando** a API/dispatcher tentar enfileirar  
**Então** o registro de outbox deve permanecer recuperável (`pending` ou
`enqueue_failed`)  
**E** o domínio (Caso) não deve ser apagado por falha de Redis  
**E** nenhum job deve ser considerado perdido.

### Cenário 4 — Reconciler recupera

**Dado** registros `pending`/`enqueue_failed` e Redis novamente saudável  
**Quando** o reconciler executar  
**Então** os registros elegíveis devem ser enfileirados na fila `default`  
**E** seus status atualizados para `enqueued`.

### Cenário 5 — Worker consome `default`

**Dado** um job enfileirado na fila `default`  
**Quando** o worker estiver em execução  
**Então** o job deve ser consumido  
**E** ao sucesso do processamento (definido na spec `03`) o outbox deve refletir
conclusão (`processed` ou equivalente).

## Critérios de pronto (DoD T3.3–T3.4)

- [x] Migração da tabela de outbox. *(T3.3)*
- [x] Enqueue cobertos por testes TDD. *(T3.3; worker no T3.4)*
- [ ] Reconciler básico coberto por pelo menos um teste de recuperação.
- [ ] Serviço worker no Compose e variáveis no `.env.example`.
- [ ] Cenários 1–5 verificáveis sem DLQ nem fila `video`.

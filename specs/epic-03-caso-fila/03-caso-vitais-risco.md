# Núcleo Caso + fila — Caso vitais, Risco e Alerta v1

## Objetivo

Definir o contrato do Caso multimodal mínimo com modalidade `vitals`: criação
idempotente vinculada a um Paciente, Artefato no MinIO, processamento via
outbox/RQ, detecção de anomalias, fusão de Risco e persistência de Alerta v1
quando o nível for MEDIO ou ALTO — sem SSE.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 21 de julho de 2026** (T3.6–T3.10).

Caso + Artefato/outbox + AnomalyEngine/Fusion → Risco + Alerta v1 (≥ MEDIO,
dedupe, sem SSE). Docs e índice atualizados.

## Escopo

- Evoluir o stub `cases` (Épico 2) para o modelo de Caso desta etapa.
- `POST` (e leitura mínima) de Caso com ≥1 modalidade; nesta etapa a modalidade
  suportada é `vitals`.
- Header `Idempotency-Key` + hash do Artefato: mesma chave/mesmo conteúdo
  devolve o Caso existente.
- Upload/gravação do CSV de vitais como Artefato no MinIO; Postgres guarda
  metadados (bucket/key, hash, modalidade).
- Pipeline: outbox → worker → AnomalyEngine (vitais) → Fusion → Risco no Caso.
- Persistência de Alerta v1 (versão `1`) se Risco ≥ MEDIO; sem feed SSE.
- Autenticação JWT; papéis `medico` e `admin` operam Casos nesta etapa.

Ficam fora desta etapa: frontend; SSE de Alertas; Justificativa rica por
template completo (Épico 7); falha parcial multi-modalidade e reprocessamento
seletivo (Épico 5); DLQ/admin; modalidades `video`/`audio`/`prescriptions`;
Azure; fila `video`; tendência de risco do Paciente; paginação avançada de
listagem.

## ADRs aplicáveis

- [ADR 0001 — Privacidade](../../docs/adr/0001-privacidade-paciente.md):
  Caso pertence a Paciente; exclusão do Paciente remove Casos/Artefatos
  (CASCADE + limpeza MinIO quando implementada).
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md):
  fixtures de `01-datasets-vitais.md` alimentam TDD e demo.
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md):
  binários no MinIO; metadados no Postgres.
- [ADR 0016 — Outbox](../../docs/adr/0016-outbox-leve.md) e
  [ADR 0002 — RQ](../../docs/adr/0002-fila-redis-worker.md): processamento
  assíncrono conforme spec `02-outbox-rq.md`.
- [ADR 0018 — Idempotência](../../docs/adr/0018-idempotencia.md): create +
  worker + dedupe de Alerta.
- [ADR 0014 — Alertas versionados](../../docs/adr/0014-alertas-versionados.md):
  nesta etapa só nasce a versão inicial (v1); reprocessamento versionado fica
  para o Épico 5/7.
- [ADR 0004](../../docs/adr/0004-auth-jwt-papeis.md) /
  [ADR 0021](../../docs/adr/0021-auth-api-papeis.md): Bearer obrigatório.

## Modelo de domínio

### Caso

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `id` | UUID | PK (evolui o stub) |
| `patient_id` | UUID | FK `patients.id` ON DELETE CASCADE |
| `status` | string | `pending` \| `processing` \| `done` \| `failed` \| `cancelled` |
| `risk_score` | float nullable | preenchido após fusão; escala **0.0–1.0** |
| `risk_level` | string nullable | `BAIXO` \| `MEDIO` \| `ALTO` |
| `idempotency_key` | string nullable | único por Operador ou global conforme implementação documentada |
| `created_at`, `updated_at` | timestamptz | |

Nesta etapa, com uma única modalidade (`vitals`), o Caso vai a `done` quando
essa modalidade concluir com sucesso; `failed` se o processamento esgotar a
falha tratada pelo worker (sem DLQ UI ainda).

### Modalidade do Caso

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `case_id` | UUID | FK |
| `modality` | string | nesta etapa: `vitals` |
| `status` | string | `pending` \| `processing` \| `done` \| `failed` \| `skipped` |
| `artifact_id` | UUID nullable | FK para Artefato |

### Artefato

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `id` | UUID | PK |
| `case_id` | UUID | FK CASCADE |
| `modality` | string | `vitals` |
| `bucket` | string | ex.: `limen` |
| `object_key` | string | chave no MinIO |
| `content_sha256` | string | hex |
| `content_type` | string | ex.: `text/csv` |

### Anomalia (vitais)

Achados produzidos pelo AnomalyEngine (persistidos ou embutidos no resultado do
Caso — a implementação escolhe desde que o GET do Caso exponha evidência mínima).

### Risco (fusão)

Com apenas `vitals` bem-sucedida, a Fusion devolve o risco parcial de vitais
como Risco do Caso (peso efetivo 1.0). Limiares de nível (escala 0.0–1.0):

| Nível | Condição |
| ----- | -------- |
| `BAIXO` | `score < 0.40` |
| `MEDIO` | `0.40 ≤ score < 0.70` |
| `ALTO` | `score ≥ 0.70` |

O AnomalyEngine deve mapear as fixtures `vitals_normal` / `vitals_medium` /
`vitals_high` para esses níveis de forma estável nos testes.

### Alerta v1

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `id` | UUID | PK |
| `case_id` | UUID | FK |
| `level` | string | `MEDIO` \| `ALTO` (espelha o Risco que disparou) |
| `version` | int | `1` nesta etapa |
| `created_at` | timestamptz | append-only |

Regras:

- Emitir **somente** se `risk_level` ∈ {`MEDIO`, `ALTO`} após fusão.
- Dedupe: no máximo um Alerta `(case_id, level, version)` — reexecução idempotente
  do worker não cria duplicata.
- Sem SSE; leitura via GET do Caso ou endpoint mínimo de Alertas do Caso.

## Contratos HTTP (mínimos)

Autenticação: `Authorization: Bearer <access_token>` em todas as rotas abaixo.
Papéis: `medico` e `admin`.

### `POST /patients/{patient_id}/cases`

Headers:

- `Idempotency-Key: <string>` (obrigatório)
- `Content-Type: multipart/form-data` **ou** JSON com referência a conteúdo —
  a implementação documenta uma forma; TDD usa a forma escolhida de modo
  consistente. Mínimo: arquivo CSV de vitais (ou body que a API persista como
  Artefato).

Sucesso primeira vez: `201 Created` com corpo incluindo `id`, `status`
(`pending` ou `processing`), `patient_id`.

Mesma `Idempotency-Key` + mesmo hash de Artefato: `200 OK` (ou `201` estável)
devolvendo o **mesmo** `id` de Caso, sem duplicar Artefato/outbox.

Paciente inexistente → `404`. Sem auth → `401`. MinIO indisponível no upload →
rejeitar criação (`503` ou `502` documentado), alinhado à ADR 0016.

### `GET /cases/{case_id}`

Sucesso `200` com: `id`, `patient_id`, `status`, `risk_score`, `risk_level`,
modalidades (status), referência de Artefato, e `alert`/`alerts` se existir.

Caso inexistente → `404`.

## Pipeline assíncrono

1. API cria Caso + Artefato (MinIO) + modalidade `vitals` + outbox (mesma
   transação Postgres quando possível).
2. Dispatcher enfileira job `default` (spec `02`).
3. Worker: marca processing → lê Artefato → AnomalyEngine → Fusion → grava
   Risco → se ≥ MEDIO cria Alerta v1 → marca modalidade/Caso `done` → outbox
   `processed`.
4. Worker já `done` na modalidade: no-op idempotente (ADR 0018).

## Cenários de aceitação

### Cenário 1 — Criar Caso com vitais

**Dado** um Paciente existente e Operador autenticado  
**Quando** enviar `POST /patients/{id}/cases` com CSV de vitais e
`Idempotency-Key`  
**Então** a resposta deve ser `201` com `status` `pending` ou `processing`  
**E** deve existir Artefato no MinIO e registro de outbox  
**E** um job deve poder ser consumido na fila `default`.

### Cenário 2 — Idempotência de criação

**Dado** um Caso já criado com chave K e hash H  
**Quando** repetir o POST com a mesma chave K e o mesmo conteúdo (hash H)  
**Então** deve devolver o mesmo `case_id`  
**E** não deve criar segundo Artefato nem segundo Alerta.

### Cenário 3 — Fixture normal → BAIXO sem Alerta

**Dado** a fixture `vitals_normal`  
**Quando** o worker processar o Caso até `done`  
**Então** `risk_level` deve ser `BAIXO`  
**E** não deve existir Alerta para o Caso.

### Cenário 4 — Fixture medium → MEDIO com Alerta v1

**Dado** a fixture `vitals_medium`  
**Quando** o worker concluir  
**Então** `risk_level` deve ser `MEDIO`  
**E** deve existir Alerta com `version: 1` e `level: MEDIO`.

### Cenário 5 — Fixture high → ALTO com Alerta v1

**Dado** a fixture `vitals_high`  
**Quando** o worker concluir  
**Então** `risk_level` deve ser `ALTO`  
**E** deve existir Alerta com `version: 1` e `level: ALTO`.

### Cenário 6 — GET após done

**Dado** um Caso `done` com Risco (e Alerta se aplicável)  
**Quando** chamar `GET /cases/{id}`  
**Então** a resposta deve incluir `risk_score`, `risk_level`, status das
modalidades e Alertas persistidos quando houver.

### Cenário 7 — Reexecução idempotente do worker

**Dado** modalidade já `done`  
**Quando** o mesmo job for reentregue (at-least-once)  
**Então** o worker não deve alterar o Risco de forma divergente  
**E** não deve duplicar Alerta `(case_id, level, version)`.

### Cenário 8 — Auth

**Dado** ausência de Bearer  
**Quando** chamar `POST` ou `GET` de Caso  
**Então** a resposta deve ser `401`.

## Critérios de pronto (DoD do Épico 3)

- [x] Fixtures documentadas (spec `01`) em uso nos testes deste contrato.
- [x] Outbox + worker `default` (spec `02`) integrados ao fluxo de Caso.
- [x] `POST` Caso vitais → processamento → `done` + Risco.
- [x] Alerta v1 persistido quando Risco ≥ MEDIO; ausente quando BAIXO.
- [x] Cenários 1–8 cobertos por TDD (pytest).
- [x] README / `docs/README.md` atualizados: Épico 3 concluído, próximo Épico 4.

# Modalidades — Áudio (Azure F0 + fallback)

## Objetivo

Entregar a modalidade `audio` do Caso: sample ≤60s versionado, análise via
Speech Azure F0 com **cache**, **fallback local** e **circuit breaker**
(Épico 5 / ADR 0015), badge de Provedor de Áudio (`azure` \| `local` \|
`cache`) no Caso, contribuição ao Risco e job na fila RQ `default`
(ADR 0020).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> Transcrições e escores de áudio são demonstração — sem diagnóstico clínico.

## Status da entrega

**Pendente** (T6.7–T6.10 ok; falta T6.11–T6.12 desta etapa E6.2).

Pré-requisito: E6.1 (vídeo) concluída nesta branch.

Etapa posterior: E6.3 Prescrições — regras + histórico + seed multimodal.

## Escopo

- Fixtures de áudio pequenos versionados (ou regeneráveis) em
  `data/fixtures/audio/`: ao menos **um** clip ≤60s (WAV PCM sintético ou
  speech de referência CC), com README de fontes (AudioSet / Medical Speech
  como catálogo; brutos grandes fora do Git/CI).
- Extensão do contrato de Caso:
  `POST /cases/{id}/modalities/audio` (multipart + `Idempotency-Key`) →
  Artefato no MinIO + job `process_modality` na fila **`default`** (não
  `video`).
- Worker `default`: processamento real (substitui stub `audio` do Épico 5):
  - Resolução do **Provedor de Áudio** via `analyze_audio` (já existente em
    `app/azure/`): `azure` \| `local` \| `cache`.
  - Cliente Azure Speech F0 **injetável** (TDD sem rede); com
    `AZURE_ENABLED=true` e credenciais, chama F0; caso contrário ou CB
    aberto → `local`.
  - **Cache** keyed por SHA-256 do conteúdo do Artefato: hit após análise
    bem-sucedida → `provider=cache` (sem nova chamada Azure).
  - Fallback local determinístico sobre a fixture (transcript/score
    sintéticos calibrados) — sem rede.
- Badge `provider` exposto em `GET /cases/{id}` na modalidade `audio`
  (e/ou metadado persistido do resultado).
- Modalidade `audio` contribui ao Risco (fusão com vitais/vídeo; falha
  parcial intacta).
- Timeout de áudio já previsto (ADR 0017, padrão 90s).
- TDD cobrindo: fixtures; upload → MinIO → fila `default`; provider
  `local` / `cache` / Azure injetado; CB aberto → `local` sem rede; fusão
  de Risco; auth.

Ficam fora desta etapa: prescrições e seed multimodal (E6.3); UI polish /
upload a11y de áudio (Épico 7); Justificativa rica por template; SSE;
Exactly-once; download obrigatório de AudioSet no CI; chamada Azure real
obrigatória no CI (`AZURE_ENABLED=false`); Prometheus; fine-tune de speech.

## ADRs aplicáveis

- [ADR 0015 — Retry / CB Azure](../../docs/adr/0015-retry-circuit-breaker-azure.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0017 — Timeouts por modalidade](../../docs/adr/0017-timeouts-por-modalidade.md)
- [ADR 0020 — Filas `video` / `default`](../../docs/adr/0020-filas-separadas-video.md)
- [ADR 0013 — Falha parcial / reprocess](../../docs/adr/0013-falha-parcial-reprocessamento.md)
- [ADR 0016 — Outbox leve](../../docs/adr/0016-outbox-leve.md)
- [ADR 0018 — Idempotência](../../docs/adr/0018-idempotencia.md)

Nenhuma ADR nova obrigatória: cache in-process keyed por SHA-256 é detalhe
de implementação sob o Provedor de Áudio (CONTEXT.md) e ADR 0015. Se surgir
necessidade de Redis compartilhado entre workers, registrar ADR antes de
codar.

## Catálogo de fontes (calibração / fixtures)

| Papel | Fonte | URL / nota |
| ----- | ----- | ---------- |
| Speech / ambient | AudioSet (referência) | https://research.google.com/audioset/ |
| Utterance médica | Medical Speech / gravação própria ≤60s CC | URL documentada no README das fixtures |

## Layout no repositório

```text
data/fixtures/audio/           # clips curtos + README + manifest
data/fixtures/audio/README.md
# opcional: scripts/prepare_audio_fixtures.py
```

## Contratos HTTP (mínimos)

### `POST /cases/{id}/modalities/audio`

Anexa a modalidade `audio` a um Caso existente (multipart do clip) com header
`Idempotency-Key`. Auth: Bearer (`medico` ou `admin`).

Resposta: Caso com modalidade `audio` em `pending`/`processing` e Artefato
referenciando o objeto no MinIO. Replay idempotente com a mesma chave + mesmo
conteúdo → mesmo Caso; chave reutilizada com conteúdo diferente → `409`.

Caso inexistente → `404`. Sem `Idempotency-Key` → `400`.

### `GET /cases/{id}` (já existente)

Deve expor modalidade `audio` (`done`/`failed`), campo **`provider`**
(`azure` \| `local` \| `cache`) quando `done`, Artefato de áudio e Risco
fundido quando o Caso fechar.

## Cenários de aceitação

### Cenário 1 — Upload e fila `default`

**Dado** um Caso existente e um clip de fixture ≤60s  
**Quando** `POST /cases/{id}/modalities/audio` com `Idempotency-Key`  
**Então** Artefato no MinIO e job `process_modality` na fila `default`  
**E** a modalidade `audio` fica `pending`/`processing`.

### Cenário 2 — Provedor `local` (Azure desligado)

**Dado** `AZURE_ENABLED=false` (padrão CI/demo)  
**Quando** o worker processar a modalidade `audio`  
**Então** `provider=local`  
**E** a modalidade fica `done` com transcript/score do analyzer local  
**E** contribui ao Risco na fusão.

### Cenário 3 — Cache

**Dado** o mesmo conteúdo de áudio já analisado com sucesso neste processo  
**Quando** processar de novo (mesmo SHA-256)  
**Então** `provider=cache`  
**E** não há nova chamada ao caminho Azure.

### Cenário 4 — Azure injetado + fallback

**Dado** Azure habilitado e cliente injetado que falha (quota/timeout)  
**Quando** processar  
**Então** fallback `local` na mesma tentativa  
**E** o circuit breaker registra a falha (ADR 0015).

### Cenário 5 — Circuit breaker aberto

**Dado** CB aberto (`LIMEN_AZURE_CB_FORCE_OPEN` ou N falhas)  
**Quando** processar  
**Então** `provider=local` **sem** invocar o callable Azure (já coberto em T5.8;
reforçar no pipeline do Caso).

### Cenário 6 — Fusão / falha parcial

**Dado** `vitals` `done` e `audio` `done`  
**Quando** a fusão ocorrer  
**Então** o Risco considera ambas  
**E** se `audio` falhar e `vitals` estiver `done`, o Caso ainda pode ficar
`done`.

### Cenário 7 — Auth

**Dado** ausência de sessão  
**Quando** enviar upload de áudio  
**Então** `401`.

## Critérios de pronto (DoD desta etapa E6.2)

- [x] Spec SDD aprovada e versionada.
- [x] Fixtures áudio + README de fontes/regeneração.
- [x] Upload → Artefato MinIO → job na fila `default`.
- [x] Analyzer local + cache + Azure injetável cobertos por TDD.
- [ ] Badge `provider` no `GET /cases/{id}`; áudio contribui ao Risco.
      *(provider persistido na modalidade; exposição HTTP = T6.11)*
- [ ] Stub de `modality=audio` do Épico 5 substituído por processamento real.
      *(pipeline real ok; fechamento badge/fusão E2E = T6.11)*
- [ ] Sem Azure real obrigatório no CI; sem UI polish (Épico 7); sem E6.3.

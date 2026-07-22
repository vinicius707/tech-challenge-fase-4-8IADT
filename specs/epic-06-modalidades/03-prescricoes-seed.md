# Modalidades — Prescrições + seed multimodal

## Objetivo

Entregar a modalidade `prescriptions` do Caso: CSV sintético versionado,
análise por **regras determinísticas** (dose / intervalo / medicamento
inesperado) com **desvio longitudinal** quando o Paciente já tiver Casos
anteriores (ADR 0010), contribuição ao Risco na fila RQ `default`
(ADR 0020), e **seed demo** com Casos multimodais
(vitais + vídeo + áudio + prescrições).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> Anomalias de Prescrição são demonstração — sem decisão terapêutica real.

## Status da entrega

**Pendente** (T6.13–T6.16 ok; falta T6.17–T6.20 desta etapa E6.3).

Pré-requisito: E6.2 (áudio) concluída nesta branch.

Etapa posterior: Épico 7 (Alertas + polish UI) — fora deste fechamento do
Épico 6.

## Escopo

- Fixtures CSV versionados (ou regeneráveis) em
  `data/fixtures/prescriptions/`: ao menos **três** cenários
  (`normal` / `medium` / `high` ou equivalentes calibrados), com README de
  schema e catálogo de referência (sem PHI; brutos externos fora do Git/CI).
- Extensão do contrato de Caso:
  `POST /cases/{id}/modalities/prescriptions` (multipart + `Idempotency-Key`)
  → Artefato no MinIO + job `process_modality` na fila **`default`**
  (não `video`).
- Worker `default`: processamento real da modalidade `prescriptions`:
  - Parser do CSV → lista de **Prescrição** (medicamento, dose, intervalo,
    timestamp relativo).
  - **Regras determinísticas** (ADR 0010): dose fora de faixa do catálogo
    local; intervalo irregular vs. esperado do medicamento; medicamento
    ausente do catálogo / inesperado.
  - **Desvio longitudinal**: se o Paciente tiver Casos anteriores com
    `prescriptions` `done`, comparar doses/medicamentos e marcar desvio
    quando a mudança exceder limiares documentados; sem histórico, só
    regras locais (demo de Caso único).
  - Saída: Anomalias + escore parcial → fusão de Risco com as demais
    modalidades `done` (falha parcial intacta).
- Timeout de prescrições alinhado ao padrão ADR 0017
  (`LIMEN_TIMEOUT_PRESCRIPTIONS_SECONDS`, padrão `30` — CSV leve como vitais).
- **Seed demo multimodal**: script (ou comando documentado) que materializa
  ao menos um Paciente + Caso(s) com Artefatos das quatro modalidades a
  partir das fixtures (sem UI; sem Azure real).
- TDD cobrindo: fixtures; upload → MinIO → fila `default`; regras sem
  histórico; desvio com histórico; fusão / falha parcial; auth; seed
  determinístico (smoke).

Ficam fora desta etapa: UI de prescrições / upload a11y (Épico 7);
integração farmácia / prescritor eletrônico real; Justificativa rica por
template; SSE; Exactly-once; ML de prescrição; PHI; Prometheus; seed
completo de entrega final / notebooks (Épico 8).

## ADRs aplicáveis

- [ADR 0010 — Prescrições regras + histórico](../../docs/adr/0010-prescricoes-regras-historico.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0013 — Falha parcial / reprocess](../../docs/adr/0013-falha-parcial-reprocessamento.md)
- [ADR 0016 — Outbox leve](../../docs/adr/0016-outbox-leve.md)
- [ADR 0017 — Timeouts por modalidade](../../docs/adr/0017-timeouts-por-modalidade.md)
- [ADR 0018 — Idempotência](../../docs/adr/0018-idempotencia.md)
- [ADR 0020 — Filas `video` / `default`](../../docs/adr/0020-filas-separadas-video.md)
- [ADR 0001 — Privacidade](../../docs/adr/0001-privacidade-paciente.md)

Nenhuma ADR nova obrigatória: catálogo local de medicamentos + limiares de
desvio são detalhe de implementação sob ADR 0010. Timeout `prescriptions`
estende ADR 0017 sem emenda (mesmo padrão vitais/áudio/vídeo). Se surgir
persistência de “plano terapêutico” separado do Caso, registrar ADR antes
de codar.

## Catálogo de fontes (calibração / fixtures)

| Papel | Fonte | URL / nota |
| ----- | ----- | ---------- |
| Schema / faixas demo | Catálogo sintético Limen | Documentado no README das fixtures |
| Referência acadêmica | Formulários públicos / bulas genéricas | Só calibração — **não** PHI nem farmácia real |

## Layout no repositório

```text
data/fixtures/prescriptions/           # CSVs + README + manifest
data/fixtures/prescriptions/README.md
# opcional: scripts/prepare_prescription_fixtures.py
# opcional: scripts/seed_multimodal_demo.py
```

## Contratos HTTP (mínimos)

### `POST /cases/{id}/modalities/prescriptions`

Anexa a modalidade `prescriptions` a um Caso existente (multipart do CSV)
com header `Idempotency-Key`. Auth: Bearer (`medico` ou `admin`).

Resposta: Caso com modalidade `prescriptions` em `pending`/`processing` e
Artefato no MinIO. Replay idempotente com a mesma chave + mesmo conteúdo →
mesmo Caso; chave reutilizada com conteúdo diferente → `409`.

Caso inexistente → `404`. Sem `Idempotency-Key` → `400`.

### `GET /cases/{id}` (já existente)

Deve expor modalidade `prescriptions` (`done`/`failed`), Artefato CSV e
Risco fundido quando o Caso fechar. Anomalias entram na Justificativa
mínima já existente via fusão (template rico = Épico 7).

## Cenários de aceitação

### Cenário 1 — Upload e fila `default`

**Dado** um Caso existente e um CSV de fixture  
**Quando** `POST /cases/{id}/modalities/prescriptions` com `Idempotency-Key`  
**Então** Artefato no MinIO e job `process_modality` na fila `default`  
**E** a modalidade `prescriptions` fica `pending`/`processing`.

### Cenário 2 — Regras sem histórico

**Dado** Paciente sem Casos anteriores com `prescriptions` `done`  
**E** CSV com dose fora de faixa (fixture `medium`/`high`)  
**Quando** o worker processar  
**Então** a modalidade fica `done` com Anomalias das regras  
**E** contribui ao Risco na fusão.

### Cenário 3 — Desvio longitudinal

**Dado** o mesmo Paciente com Caso anterior `done` contendo `prescriptions`  
**E** o novo CSV com dose/medicamento desviando além do limiar  
**Quando** processar o novo Caso  
**Então** há Anomalia de desvio longitudinal  
**E** o escore parcial reflete o desvio (além das regras locais).

### Cenário 4 — Fusão / falha parcial

**Dado** `vitals` `done` e `prescriptions` `done`  
**Quando** a fusão ocorrer  
**Então** o Risco considera ambas  
**E** se `prescriptions` falhar e `vitals` estiver `done`, o Caso ainda
pode ficar `done`.

### Cenário 5 — Seed multimodal

**Dado** a stack local (ou stores in-memory no TDD do script)  
**Quando** executar o seed demo documentado  
**Então** existe ao menos um Caso com Artefatos das modalidades
`vitals`, `video`, `audio` e `prescriptions`  
**E** o seed é determinístico / idempotente o bastante para demo.

### Cenário 6 — Auth

**Dado** ausência de sessão  
**Quando** enviar upload de prescrições  
**Então** `401`.

## Critérios de pronto (DoD desta etapa E6.3)

- [x] Spec SDD aprovada e versionada.
- [x] Fixtures CSV + README de schema/regeneração.
- [x] Upload → Artefato MinIO → job na fila `default`.
- [ ] Engine de regras + desvio longitudinal cobertos por TDD.
      *(regras locais = T6.16; desvio longitudinal = T6.17)*
- [ ] Modalidade contribui ao Risco; falha parcial intacta.
- [ ] Seed demo multimodal documentado e coberto por smoke/TDD.
- [ ] Sem UI de prescrições (Épico 7); sem farmácia real; sem Épico 8.
- [ ] README operacional + índice `docs/README.md` atualizados.

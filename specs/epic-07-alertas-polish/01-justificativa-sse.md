# Alertas + polish — Justificativa template e SSE (E7.1)

## Objetivo

Expor a **Justificativa** do Risco (template, sem LLM) no detalhe do Caso e
entregar o **feed SSE de Alertas** autenticado com `fetch` + Bearer — sobre
Alertas versionados já persistidos (Épicos 3/5).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 22 de julho de 2026** (T7.0–T7.5: specs, Justificativa template,
SSE Bearer, UI mínima, cliente fetch e fechamento docs).

Etapas posteriores do Épico 7 (specs próprias):

- E7.2 — Telas estrela + a11y AA + dark mode + DLQ UI (concluída)
- E7.3 — Gate Lighthouse por regressão vs baseline (concluída)

## Escopo

- **Justificativa** no `GET /cases/{id}` (e/ou campo dedicado estável):
  contribuições por modalidade `done` (peso/risco parcial + principais
  Anomalias), modalidades `failed`/`skipped` listadas como indisponíveis, e
  narrativa curta gerada por **template determinístico** (sem LLM).
- UI mínima na tela `/casos/[id]`: bloco Justificativa legível (sem polish
  AA/tema desta etapa — fica em E7.2).
- Endpoint SSE de Alertas (escopo global do Operador autenticado ou filtrável
  por Paciente — documentar no contrato): eventos `alert.created` /
  `alert.updated` (nova versão append-only) com payload mínimo
  (`alert_id`, `case_id`, `level`, `version`, `created_at`).
- Cliente frontend: consumo via `fetch` + `Authorization: Bearer` +
  `ReadableStream` (ADR 0022); **não** usar `EventSource` nativo nem token
  na query string.
- Heartbeat/keep-alive documentado; reconexão simples no cliente (backoff
  leve) sem inventar broker aparte (Redis pub/sub ou polling interno aceitável
  se justificado na implementação — sem nova ADR se seguir ADR 0022).
- TDD: template Justificativa estável; SSE emite após fusão ≥ MEDIO; nova
  versão em reprocess gera evento; `401` sem Bearer.

Ficam fora desta etapa: dark mode / WCAG 2.2 AA fino (E7.2); upload a11y;
toast/região Alertas navegável; admin DLQ UI; Recharts; gate Lighthouse
(E7.3); e-mail/push; Justificativa por LLM; Épico 8 (CI/CD/GHCR).

## ADRs aplicáveis

- [ADR 0014 — Alertas versionados](../../docs/adr/0014-alertas-versionados.md)
- [ADR 0022 — SSE via fetch + Bearer](../../docs/adr/0022-sse-fetch-stream.md)
- [ADR 0013 — Falha parcial / reprocess](../../docs/adr/0013-falha-parcial-reprocessamento.md)
- [ADR 0004 — Auth JWT / papéis](../../docs/adr/0004-auth-jwt-papeis.md)
- [ADR 0021 — Auth API / papéis](../../docs/adr/0021-auth-api-papeis.md)

Nenhuma decisão nova de arquitetura identificada (SSE e Alertas já decididos).

## Contratos HTTP (mínimos)

Autenticação Bearer; papéis `medico` e `admin`.

### `GET /cases/{case_id}`

Estende a resposta existente com Justificativa, por exemplo:

```json
{
  "justification": {
    "narrative": "string (template)",
    "modalities": [
      {
        "modality": "vitals",
        "status": "done",
        "weight": 0.25,
        "partial_score": 0.8,
        "partial_level": "ALTO",
        "top_anomalies": ["hr_high"]
      }
    ]
  },
  "alerts": [{ "id": "...", "level": "ALTO", "version": 1, "created_at": "..." }]
}
```

Shape exacto pode ajustar-se na TDD desde que cubra contribuições + narrativa
template + alertas versionados.

### `GET /alerts/stream` (SSE)

- `Content-Type: text/event-stream`
- Header `Authorization: Bearer` obrigatório (`401` sem)
- Eventos nomeados (`event: alert.created` / `alert.updated`) + `data:` JSON
- Sem token na query

## Cenários de aceitação

### Cenário 1 — Justificativa após fusão

**Dado** um Caso `done` com ≥1 modalidade `done` e Risco calculado  
**Quando** chamar `GET /cases/{id}`  
**Então** a resposta inclui Justificativa com narrativa template não vazia  
**E** lista contribuições só de modalidades `done`  
**E** modalidades `failed` aparecem como indisponíveis (sem peso na fusão).

### Cenário 2 — Template determinístico

**Dado** o mesmo Caso (mesmos riscos parciais / anomalias)  
**Quando** gerar a Justificativa duas vezes  
**Então** a narrativa e a estrutura de contribuições são idênticas  
**E** não há chamada a LLM / Azure OpenAI.

### Cenário 3 — SSE emite Alerta v1

**Dado** Operador autenticado conectado a `GET /alerts/stream`  
**Quando** um Caso concluir com Risco ≥ MEDIO e persistir Alerta v1  
**Então** o stream recebe evento `alert.created` (ou equivalente) com
`level`, `version=1`, `case_id`.

### Cenário 4 — SSE em nova versão

**Dado** Caso com Alerta v1 e cliente SSE conectado  
**Quando** reprocessamento gerar Alerta v2 (mudança de nível)  
**Então** o stream recebe `alert.updated` (ou `alert.created` da v2)
preservando histórico append-only no GET do Caso.

### Cenário 5 — Auth SSE

**Dado** ausência de Bearer  
**Quando** abrir o stream  
**Então** `401`.

### Cenário 6 — UI mínima

**Dado** Caso com Justificativa no detalhe  
**Quando** abrir `/casos/[id]` autenticado  
**Então** a Justificativa é visível (texto)  
**E** (opcional nesta etapa) indicador de Alertas via SSE sem polish AA.

## Critérios de pronto (DoD desta etapa E7.1)

- [x] Justificativa template no contrato do Caso + testes TDD.
- [x] SSE `fetch`+Bearer conforme ADR 0022; sem token na query.
- [x] Eventos cobrem criação e nova versão de Alerta.
- [x] UI mínima da Justificativa em `/casos/[id]`.
- [x] Sem dark/AA/DLQ UI/Lighthouse gate (E7.2/E7.3).
- [x] README / índice docs atualizados no fechamento da etapa.

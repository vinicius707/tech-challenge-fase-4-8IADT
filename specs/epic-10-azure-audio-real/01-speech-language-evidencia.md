# Épico 10 — Azure áudio real (Speech + Text Analytics)

## Objetivo

Substituir o stub de Azure do Épico 6.2 por integração **real** opt-in:
Azure Speech (Transcrição pt-BR) + Azure Text Analytics (Sentimento + key
phrases), com lista local de Termos Críticos, Anomalias de NLP na modalidade
`audio`, Artefato de Transcrição e evidência commitada — sem quebrar o CI
offline (`AZURE_ENABLED=false`).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> Transcrições, Sentimento e Termos Críticos são demonstração — sem diagnóstico.

## Status da entrega

**Concluída** (T10.0–T10.6). Spec SDD, Speech + Language opt-in, Termos Críticos,
Artefato de Transcrição, evidência TTS e fechamento de docs.

Relação com E6.2: o Épico 6.2 permanece **Concluída** (seam: upload, fila,
Provedor de Áudio, cache, CB, analyzer local, Azure **injetável**). Este épico
entrega o caminho **real** atrás do mesmo seam (ADR 0030 / 0031).

Ordem de implementação das frentes de IA real: **Épico 10 → Épico 11 (YOLOv8)
→ Épico 9 (Vitais ML)**. O Épico 9 tem specs prontas; **implementação não
iniciada** — não está encerrado.

## Escopo

- Cliente Azure Speech **real** (SDK) pt-BR, injetável nos testes; ativado só
  com `AZURE_ENABLED=true` + `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`.
- Azure Text Analytics (Language): Sentimento + key phrases sobre a
  Transcrição; `AZURE_LANGUAGE_KEY` + `AZURE_LANGUAGE_ENDPOINT`.
- Lista determinística PT-BR de Termos Críticos (sempre local) → Anomalia(s)
  da modalidade `audio` quando há Transcrição **real**.
- Sentimento fortemente negativo → Anomalia da modalidade `audio`.
- Score da modalidade: `max(score_acústico_ou_stt, score_nlp)` com regras
  determinísticas calibradas na implementação (ex.: ≥1 Termo Crítico → score
  ≥ 0.70; Sentimento fortemente negativo → ≥ 0.55; ambos → ≥ 0.85).
- Transcrição real persistida como Artefato de texto no MinIO.
- Badge `provider`: `azure` se Speech produziu a Transcrição; Language é
  metadado de disponibilidade (`language_available` ou ausência de Sentimento).
  CB (ADR 0015) rege **Speech**; falha de Language não abre o CB de Speech.
- Fixture TTS pt-BR ≤60s (crítica e/ou neutra) +
  `scripts/gerar-evidencia-audio.sh` commitando em `data/evidencia/audio/`.
- Orquestrador fino `scripts/gerar-evidencia-real.sh` que nesta entrega só
  chama o script de áudio (Épicos 11/9 acrescentam etapas).
- TDD: Speech/Language injetados (sem rede no CI); Termos Críticos sobre texto
  injetado; degradação Speech/Language independente; regressão E6.2 com
  `AZURE_ENABLED=false`.
- `.env.example` com placeholders das quatro vars Speech/Language.

Ficam fora desta etapa: YOLOv8 (Épico 11); Isolation Forest / AE (Épico 9);
UI nova de Transcrição/Termos; Exactly-once; Prometheus; Text Analytics for
Health; fine-tune de speech; job CI com secrets Azure; chamada Azure real
obrigatória no CI.

## ADRs aplicáveis

- [ADR 0030 — IA real opt-in + evidência](../../docs/adr/0030-ia-real-opt-in-evidencia.md)
- [ADR 0031 — Áudio NLP / Anomalias](../../docs/adr/0031-audio-nlp-modelagem.md)
- [ADR 0015 — Retry / CB Azure](../../docs/adr/0015-retry-circuit-breaker-azure.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0017 — Timeouts por modalidade](../../docs/adr/0017-timeouts-por-modalidade.md)
- Spec seam: [`../epic-06-modalidades/02-audio-azure.md`](../epic-06-modalidades/02-audio-azure.md)

## Contrato de configuração

| Variável | Função | Default CI |
| -------- | ------ | ---------- |
| `AZURE_ENABLED` | Master switch do caminho Azure | `false` |
| `AZURE_SPEECH_KEY` | Chave Speech | vazio |
| `AZURE_SPEECH_REGION` | Região Speech | vazio |
| `AZURE_LANGUAGE_KEY` | Chave Language / Text Analytics | vazio |
| `AZURE_LANGUAGE_ENDPOINT` | Endpoint Language | vazio |

Sem Speech key (mesmo com `AZURE_ENABLED=true`) → fallback `local` para fala.
Sem Language key → Transcrição ok; Sentimento indisponível; Termos Críticos
locais ainda rodam **se** houver Transcrição real.

## Regras de domínio (fechadas no grilling)

1. **Provedor de Áudio** = origem da **fala** (Speech). Language não redefine o badge.
2. **Termo Crítico** só sobre Transcrição real (não placeholder
   `local-transcript-{hash}`).
3. Caminho `local` puro → sem Termos Críticos, sem Sentimento; score acústico
   determinístico do E6.2 permanece.
4. Score áudio = `max(acústico/stt, nlp)` com Anomalias listando evidências.
5. Evidência de áudio versionada neste épico; orquestrador cresce depois.

## Cenários de aceitação

### Cenário 1 — CI / regressão E6.2

**Dado** `AZURE_ENABLED=false` (CI)  
**Quando** `uv run pytest` e processar fixture de áudio  
**Então** `provider=local`, sem rede, sem SDK obrigatório no caminho crítico  
**E** testes E6.2 existentes continuam verdes.

### Cenário 2 — Speech real (injetado no TDD; SDK na evidência)

**Dado** `AZURE_ENABLED=true`, Speech disponível (cliente real ou injetado)  
**Quando** processar áudio com fala pt-BR  
**Então** `provider=azure`, Transcrição não vazia  
**E** Artefato de texto da Transcrição no MinIO  
**E** Termos Críticos locais avaliados sobre essa Transcrição.

### Cenário 3 — Language ausente, Speech ok

**Dado** Speech ok e Language sem chave / falha  
**Quando** processar  
**Então** `provider=azure`, Transcrição presente, Sentimento ausente  
**E** Termos Críticos locais ainda podem gerar Anomalias  
**E** o CB de Speech **não** abre por falha de Language.

### Cenário 4 — Termo Crítico → Anomalia + score

**Dado** Transcrição contendo ao menos um Termo Crítico da lista  
**Quando** finalizar análise de áudio  
**Então** existe Anomalia de modalidade `audio` com evidência = trecho  
**E** score da modalidade ≥ limiar NLP documentado (≥ 0.70 se só termos).

### Cenário 5 — Sentimento fortemente negativo

**Dado** Language retorna polaridade fortemente negativa  
**Quando** finalizar análise  
**Então** Anomalia de Sentimento na modalidade `audio`  
**E** score ≥ 0.55 (ou ≥ 0.85 se também houver Termo Crítico).

### Cenário 6 — Local puro sem NLP inventado

**Dado** analyzer local com placeholder `local-transcript-{hash}`  
**Quando** processar  
**Então** nenhuma Anomalia de Termo Crítico ou Sentimento  
**E** score permanece o determinístico acústico.

### Cenário 7 — Cache

**Dado** mesmo SHA-256 já analisado com sucesso  
**Quando** processar de novo  
**Então** `provider=cache` sem nova chamada Speech/Language.

### Cenário 8 — Evidência commitada

**Dado** credenciais F0 locais e fixture TTS  
**Quando** `./scripts/gerar-evidencia-audio.sh`  
**Então** artefatos em `data/evidencia/audio/` (JSON de Transcrição,
Sentimento, Termos Críticos, metadados) prontos para commit  
**E** `gerar-evidencia-real.sh` delega a este script.

## Tarefas planejadas (uma por commit, sessões futuras)

| Tarefa | Conteúdo |
| ------ | -------- |
| T10.0 | Esta spec + notas de índice / CONTEXT / E6.2 (docs) — **feita** |
| T10.1 | Env + cliente Speech real injetável + TDD — **feita** |
| T10.2 | Text Analytics + degradação independente + TDD — **feita** |
| T10.3 | Termos Críticos + score `max(acústico, nlp)` + Anomalias — **feita** |
| T10.4 | Artefato de Transcrição no MinIO — **feita** |
| T10.5 | Fixture TTS + `gerar-evidencia-audio.sh` + orquestrador fino — **feita** |
| T10.6 | Fechamento docs (README, `.env.example`, índice) — **feita** |

Branch sugerida: `feature/limen-epic-10-azure-audio-real` a partir de `main`.

## Critérios de pronto (DoD E10)

- [x] Spec SDD aprovada (esta) + docs/ADRs da T10.0.
- [x] Speech + Language reais opt-in, TDD sem rede no CI.
- [x] Termos Críticos locais + Sentimento → Anomalias; score `max(...)`.
- [x] Transcrição real como Artefato; badge = origem da fala.
- [x] Evidência em `data/evidencia/audio/` via script versionado.
- [x] `.env.example` / README / índice atualizados.
- [x] Sem Azure obrigatório no CI; sem UI nova; sem Épicos 11/9.

# Modelagem do áudio NLP: Termo Crítico e Sentimento como Anomalias

Ao ligar Azure Speech (Transcrição) e Text Analytics (Sentimento + key phrases),
os achados de NLP **reaproveitam** o conceito de Anomalia em vez de criar um
fluxo paralelo: um **Termo Crítico** detectado na Transcrição ou um **Sentimento**
fortemente negativo geram Anomalias da modalidade áudio, com evidência = trecho
da Transcrição (+ timestamp quando aplicável). Assim eles fluem pela máquina
existente de fusão → Risco → Alerta sem código novo de agregação.

A Transcrição é persistida como **Artefato de texto** no object store (o Caso
referencia a chave, não o conteúdo), coerente com o modelo de Artefato já
definido. `Transcrição`, `Termo Crítico` e `Sentimento` também ganham verbetes
próprios no `CONTEXT.md` para a linguagem ubíqua ficar precisa (decisão “misto”:
reusa Anomalia no runtime **e** formaliza os termos no glossário).

## Degradação graciosa (regra de negócio)

- Sem Azure Speech → sem Transcrição **real**; o fallback local pode emitir
  placeholder `local-transcript-{hash}`, que **não** dispara Termo Crítico nem
  Sentimento.
- Com Transcrição real e sem Azure Language → sem Sentimento; a lista local de
  Termos Críticos **ainda roda** sobre a Transcrição (algoritmo sempre local).
- O badge `Provedor de Áudio` reflete a origem da **fala** (Speech); `azure` não
  implica que Language respondeu.
- Emenda (grilling Épico 10): Termo Crítico exige Transcrição real — a lista é
  local, mas não inventa achados a partir do placeholder do E6.2.

## Alternativas rejeitadas

| Alternativa | Motivo |
| ----------- | ------ |
| Transcrição/Sentimento/Termo Crítico como entidades de primeira classe no runtime | Duplica o pipeline de fusão/alerta já existente sobre Anomalia |
| Sentimento apenas como contexto (fora da fusão) | Perde sinal clínico relevante que o edital pede (sentimentos) |
| Termo Crítico dependente exclusivamente do Azure | Quebra a degradação graciosa; sem Azure a modalidade áudio ficaria cega |
| Transcrição inline no resultado (não Artefato) | Vaza texto potencialmente sensível para fora do object store; foge do modelo de Artefato |

# Épico 9 — Isolation Forest no VitalsAnomalyEngine (E9.2)

## Objetivo

Introduzir Isolation Forest (sklearn + joblib) no caminho de vitais atrás da
flag `LIMEN_VITALS_BACKEND`, com artefato de modelo **pequeno versionado** e
**CI default em `thresholds`**.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** — spec apenas (SDD). Depende de E9.1 para dados de treino full;
o modelo pequeno no Git pode ser gerado a partir de amostra processada ou
features derivadas das fixtures + amostra ETL.

## Escopo

- Extensão de `VitalsAnomalyEngine` (ou módulo irmão) com backends:
  - `thresholds` — comportamento atual (bit-a-bit nos testes existentes);
  - `isolation_forest` — carrega `models/vitals/*.joblib` (caminho documentado);
  - `hybrid` — limiares **OU** anomalia IF (regra documentada na implementação).
- Env: `LIMEN_VITALS_BACKEND` (default `thresholds` em CI e `.env.example`).
- Deps: `scikit-learn` + `joblib` no backend (grupo runtime ou dependency
  explícita — decisão fina na implementação, desde que a imagem continue
  aceitável e o CI não baixe datasets).
- Script `scripts/train_vitals_if.py` (nome final livre) que treina o modelo
  full a partir de `data/processed/` e pode emitir o artefato pequeno.
- Testes TDD:
  - default `thresholds` → suíte atual verde sem arquivo de modelo obrigatório
    em todos os jobs, **ou** modelo pequeno sempre presente no Git;
  - com `isolation_forest` / `hybrid` + artefato → anomalias/risco coerentes
    nas fixtures `medium`/`high`.
- Compose local: documentar `LIMEN_VITALS_BACKEND=hybrid` para demo/vídeo.

Ficam fora desta etapa: carregar PyTorch/AE no worker; alterar limiares
numéricos históricos sem flag; ETL (E9.1); notebook AE (E9.3); relatório/roteiro
(E9.4).

## ADRs aplicáveis

- [ADR 0029 — Vitais ML híbrido](../../docs/adr/0029-vitais-ml-hibrido.md)
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md)
- [ADR 0018 — Idempotência](../../docs/adr/0018-idempotencia.md) (Caso inalterado
  no contrato HTTP)

## Contrato de configuração

| Variável | Valores | Default CI | Default demo local (doc) |
| -------- | ------- | ---------- | ------------------------ |
| `LIMEN_VITALS_BACKEND` | `thresholds` \| `isolation_forest` \| `hybrid` | `thresholds` | `hybrid` |

## Cenários de aceitação

### Cenário 1 — CI / regressão

**Dado** `LIMEN_VITALS_BACKEND=thresholds` (ou unset = thresholds)  
**Quando** `uv run pytest`  
**Então** testes de vitais/Caso existentes passam sem mudança de expectativa
de Risco nas fixtures canônicas.

### Cenário 2 — Isolation Forest

**Dado** artefato pequeno em `models/vitals/` e backend `isolation_forest`  
**Quando** processar `vitals_high.csv`  
**Então** o Caso produz Anomalias/Risco não triviais (nível ≥ MEDIO alinhado à
fixture).

### Cenário 3 — Hybrid

**Dado** backend `hybrid`  
**Quando** uma série dispara só limiar **ou** só IF  
**Então** a Anomalia/Risco reflete a união documentada (OR).

### Cenário 4 — Sem Torch no worker

**Dado** o ambiente do worker/backend  
**Quando** inspecionar dependências instaladas na imagem de produção  
**Então** não há `torch` / TensorFlow como dependência obrigatória.

## Critérios de pronto (DoD E9.2)

- [ ] Spec SDD aprovada (esta).
- [ ] Flag + backends implementados com TDD.
- [ ] Modelo pequeno versionado + script de treino documentado.
- [ ] `.env.example` e README atualizados.
- [ ] CI permanece em `thresholds`; smoke não exige download de dataset.
- [ ] Sem PyTorch no Dockerfile do backend.

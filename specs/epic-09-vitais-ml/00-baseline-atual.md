# Épico 9 — Baseline pré-ML (estado atual)

## Objetivo

Congelar o **estado atual** do Limen (pós Épicos 1–8) como referência de
comparação **antes** de qualquer implementação de ETL / Isolation Forest /
autoencoder. Este documento **não** entrega código novo.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status

**Épico 9 concluído (T9.0–T9.4).** Este arquivo congela o **antes** (só limiares,
sem sklearn no runtime histórico). O **depois** está no relatório §5.3,
`compare_vitals_ml.ipynb` e ADR 0029.

## Tarefas planejadas (uma por commit, sessões futuras)

| Tarefa | Spec | Conteúdo |
| ------ | ---- | -------- |
| T9.0 | esta | Congelar baseline + ADR/specs (docs only) — **feita** |
| T9.1 | `01` | ETL offline — **feita** |
| T9.2 | `02` | IF + flag no runtime — **feita** |
| T9.3 | `03` | Notebook AE PyTorch + export — **feita** |
| T9.4 | `04` | Comparação + relatório + roteiro — **feita** |

Branch sugerida: `feature/limen-epic-09-vitais-ml` a partir de `main`.

## O que é verdade hoje (fatos)

| Área | Estado atual |
| ---- | ------------ |
| `VitalsAnomalyEngine` | Só limiares (`heart_rate` / `spo2`) em `backend/app/cases/vitals_engine.py` |
| Datasets públicos | Catálogo + relatório/notebooks; **sem** download em runtime/CI |
| Fixtures | `data/fixtures/vitals/{normal,medium,high}.csv` via `scripts/calibrate_vitals.py` |
| Backend deps | Sem `scikit-learn`, `joblib`, `torch` (`backend/pyproject.toml`) |
| Docker API | `python:3.12-slim` + `uv sync --frozen --no-dev` |
| CI | pytest + Lighthouse + GHCR + smoke vitais; notebooks **fora** do gate |
| Demo | `./scripts/start-limen.sh` → `./scripts/seed-multimodal-demo.sh` |
| ADRs vitais | [0008](../../docs/adr/0008-vitais-sinteticos.md); extensão planejada [0029](../../docs/adr/0029-vitais-ml-hibrido.md) |

## Como rodar o baseline (sem ML)

```bash
# Na raiz do repo
./scripts/start-limen.sh
./scripts/seed-multimodal-demo.sh
# UI: http://localhost:3000  |  API docs: http://localhost:8000/docs
```

Smoke só vitais (alinhado ao CI):

```bash
./scripts/smoke-caso-vitais.sh
```

Validação backend (estado atual):

```bash
cd backend
uv sync --frozen
uv run python -m compileall -q app migrations tests
uv run pytest
```

## O que comparar depois do Épico 9

1. Mesmos CSVs de fixture → Risco com `thresholds` vs `hybrid` / `isolation_forest`.
2. Imagem Docker / `pyproject.toml`: presença de sklearn só onde a ADR 0029 permite.
3. Notebook: curvas de loss do AE (hoje inexistentes) vs EDA atual.
4. Relatório e roteiro: seção ML / comparação vs texto só de limiares.

## Ficam fora deste documento

Qualquer código de treino, flag de backend, deps ML, alteração de seed ou CI.
Isso começa nas specs `01`–`04` e só após sessão de implementação dedicada.

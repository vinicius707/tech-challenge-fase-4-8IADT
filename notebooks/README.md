# Notebooks Limen (Fase 4)

Evidência exploratória e de calibração — **não** rodam no CI e **não** baixam
datasets brutos.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

| Notebook | Conteúdo |
| -------- | -------- |
| [`eda_vitals_inicial.ipynb`](eda_vitals_inicial.ipynb) | EDA inicial (Épico 3) — fixtures vitais |
| [`eda_vitals_final.ipynb`](eda_vitals_final.ipynb) | EDA final — faixas, calibração, catálogo (Kaggle, Hospital Deterioration, PhysioNet) |
| [`evidencia_modalidades.ipynb`](evidencia_modalidades.ipynb) | Evidência multimodal — vídeo, áudio, prescriptions + catálogo (AudioSet, 3DYoga90, …) |
| [`train_vitals_autoencoder.ipynb`](train_vitals_autoencoder.ipynb) | AE PyTorch (epochs/loss/early stopping) — só portfólio; **fora** do worker |
| [`compare_vitals_ml.ipynb`](compare_vitals_ml.ipynb) | Comparação limiares vs IF vs AE (precision/recall/agreement) — Épico 9.4 |

Fixtures versionadas: `data/fixtures/`. Regenerar: scripts em `scripts/`
(`calibrate_vitals.py`, `prepare_video_fixtures.py`, …). Brutos opcionais em
`data/raw/` (gitignored).

## Ambiente ML (autoencoder — Épico 9)

PyTorch **não** entra na imagem da API nem no `uv sync` do backend. Use um
venv separado:

```bash
python -m venv .venv-ml
source .venv-ml/bin/activate   # Windows: .venv-ml\Scripts\activate
pip install -r notebooks/requirements-ml.txt
jupyter notebook notebooks/train_vitals_autoencoder.ipynb
```

Para a comparação (`compare_vitals_ml.ipynb`), o venv do `backend/` (sklearn)
basta para limiares + IF; Torch é opcional para a linha do AE.

O CI **não** instala `requirements-ml.txt` nem executa notebooks AE/comparação
([ADR 0029](../docs/adr/0029-vitais-ml-hibrido.md)). Export opcional:
`models/vitals/ae_export.pt` (gitignored).

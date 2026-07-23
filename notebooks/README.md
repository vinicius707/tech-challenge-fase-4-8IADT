# Notebooks Limen (Fase 4)

Evidência exploratória e de calibração — **não** rodam no CI e **não** baixam
datasets brutos.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

| Notebook | Conteúdo |
| -------- | -------- |
| [`eda_vitals_inicial.ipynb`](eda_vitals_inicial.ipynb) | EDA inicial (Épico 3) — fixtures vitais |
| [`eda_vitals_final.ipynb`](eda_vitals_final.ipynb) | EDA final — faixas, calibração, catálogo (Kaggle, Hospital Deterioration, PhysioNet) |
| [`evidencia_modalidades.ipynb`](evidencia_modalidades.ipynb) | Evidência multimodal — vídeo, áudio, prescriptions + catálogo (AudioSet, 3DYoga90, …) |

Fixtures versionadas: `data/fixtures/`. Regenerar: scripts em `scripts/`
(`calibrate_vitals.py`, `prepare_video_fixtures.py`, …). Brutos opcionais em
`data/raw/` (gitignored).

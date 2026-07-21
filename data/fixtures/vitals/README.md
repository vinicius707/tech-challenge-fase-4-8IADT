# Fixtures de sinais vitais (sintéticos)

Séries **sintéticas e versionadas** para TDD, demo e runtime do Limen.
Não contêm PHI (sem CPF, nome civil, prontuário ou IDs reais).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Calibração

| Campo | Valor |
| ----- | ----- |
| Versão | `2026-07-21.1` |
| Script | `python scripts/calibrate_vitals.py` (na raiz do repo) |
| Amostras | 60 pontos, intervalo 60 s (`timestamp` = offset em segundos, zero-pad 4) |
| Seed | `20260721` (ruído determinístico no script) |

### SHA-256 (bit-a-bit)

| Arquivo | SHA-256 |
| ------- | ------- |
| `vitals_normal.csv` | `97dc536ceb4e09a2700c4c6e45b6ea2ef059cfdfe201e09bd7579ed5eb97ee03` |
| `vitals_medium.csv` | `836aa8ecbed3b191a7d7210ec091397934292590df5d79d69d79913383e4944f` |
| `vitals_high.csv` | `5abd2bd35d29bf89c8e9e950639e69183bac0e42df308251fb475657e9d13d60` |

## Schema

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `timestamp` | string numérica | offset em segundos, ordenável |
| `heart_rate` | float | bpm |
| `spo2` | float | % |
| `systolic_bp` | float | mmHg |
| `diastolic_bp` | float | mmHg |
| `respiratory_rate` | float | rpm |
| `label` | `normal` \| `anomaly` | só calibração/validação |

## Cenários

| Arquivo | Intenção | Anomalia |
| ------- | -------- | -------- |
| `vitals_normal.csv` | Risco esperado **BAIXO** | nenhuma |
| `vitals_medium.csv` | Risco esperado **MEDIO** | a partir de `t=1200` (índice 20) |
| `vitals_high.csv` | Risco esperado **ALTO** | a partir de `t=900` (índice 15) |

Limiares numéricos de Risco: [`specs/epic-03-caso-fila/03-caso-vitais-risco.md`](../../../specs/epic-03-caso-fila/03-caso-vitais-risco.md).

## Catálogo de datasets (referência — não usados em runtime)

| Papel | Dataset | URL |
| ----- | ------- | --- |
| Primário (CSV Kaggle) | Human vital signs | https://www.kaggle.com/datasets/engrarri21/human-vital-signs |
| Eventos (opcional) | Patient Vital Signs and Event Tracking | https://www.kaggle.com/datasets/parmajha/patient-vital-signs-and-event-tracking |
| Deterioração | Hospital Deterioration | https://www.kaggle.com/datasets/tarekmasryo/hospital-deterioration-dataset · https://huggingface.co/datasets/tarekmasryo/hospital-deterioration-dataset · https://github.com/tarekmasryo/hospital-deterioration-dataset |

Brutos grandes (se baixados localmente) ficam em `data/raw/` (gitignored).
O CI e a API **não** dependem desses downloads.

## Regenerar

```bash
python scripts/calibrate_vitals.py
```

A saída deve coincidir com os SHA-256 acima. EDA exploratória:
[`notebooks/eda_vitals_inicial.ipynb`](../../../notebooks/eda_vitals_inicial.ipynb).

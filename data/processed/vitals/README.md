# Vitais processados (ETL offline)

Artefatos gerados por `scripts/etl_vitals_datasets.py` para treino do
Isolation Forest (Épico 9.2) e notebook do autoencoder (Épico 9.3).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

Os CSVs de saída (`train_rows.csv`, `train_features.csv`) são **gitignored**.
Este README fica versionado. Fixtures sintéticas em
`data/fixtures/vitals/` continuam intactas para TDD/demo ([ADR 0008](../../../docs/adr/0008-vitais-sinteticos.md)).

## Schema — `train_rows.csv`

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `timestamp` | string | offset ou valor original normalizado |
| `heart_rate` | float | bpm |
| `spo2` | float | % |
| `systolic_bp` | float | mmHg |
| `diastolic_bp` | float | mmHg |
| `respiratory_rate` | float | rpm |
| `label` | `normal` \| `anomaly` | calibração / holdout |
| `source` | string | `human_vital_signs` \| `hospital_deterioration` \| `fixtures` |

## Schema — `train_features.csv`

Mesmas métricas numéricas + `label` + `source` (sem `timestamp`), prontas para
sklearn / notebook. Sem PHI.

## Regenerar

```bash
# Brutos em data/raw/ (ver ../raw/README.md)
python scripts/etl_vitals_datasets.py

# Ou só fixtures (reproduzível, sem download)
python scripts/etl_vitals_datasets.py --from-fixtures

# Destino / seed explícitos
python scripts/etl_vitals_datasets.py --from-fixtures \
  --out-dir data/processed/vitals --seed 20260721
```

Referência: [ADR 0029](../../../docs/adr/0029-vitais-ml-hibrido.md) ·
spec [`01-etl-datasets-vitais.md`](../../../specs/epic-09-vitais-ml/01-etl-datasets-vitals.md).

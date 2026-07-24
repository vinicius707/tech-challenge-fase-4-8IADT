# Brutos de sinais vitais (opcional, gitignored)

Coloque aqui CSVs baixados **manualmente** para o ETL offline do Épico 9.
O CI, a API e o smoke **não** baixam esses arquivos.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Layout

```text
data/raw/
  README.md                          # este arquivo (versionado)
  human_vital_signs/*.csv            # Kaggle Human vital signs
  hospital_deterioration/*.csv       # amostra Hospital Deterioration
```

PhysioNet permanece **apenas citação** no relatório — sem pasta de parse
obrigatório neste épico ([ADR 0029](../../docs/adr/0029-vitais-ml-hibrido.md)).

## Fontes (URLs / licença resumida)

| Fonte | URL | Licença / nota |
| ----- | --- | -------------- |
| Human vital signs (Kaggle) | https://www.kaggle.com/datasets/engrarri21/human-vital-signs | Termos Kaggle do dataset; uso acadêmico local |
| Hospital Deterioration | https://www.kaggle.com/datasets/tarekmasryo/hospital-deterioration-dataset · https://huggingface.co/datasets/tarekmasryo/hospital-deterioration-dataset · https://github.com/tarekmasryo/hospital-deterioration-dataset | Ver página do autor; amostra local |
| PhysioNet (citação) | https://physionet.org/ | Sem download obrigatório no Limen |

Não versione PHI real. Remova colunas de identificação antes de rodar o ETL.

## Colunas aceitas (aliases)

O script mapeia aliases comuns para o schema Limen
(`heart_rate`, `spo2`, `systolic_bp`, `diastolic_bp`, `respiratory_rate`,
`label`). Exemplos: `Heart Rate` / `HR`, `SpO2`, `SBP` / `SystolicBP`,
`deterioration` / `Label` (`0`/`1` → `normal`/`anomaly`).

## Regenerar processados

Na raiz do repo:

```bash
# Com brutos locais
python scripts/etl_vitals_datasets.py

# Sem brutos: gera a partir das fixtures sintéticas (sem download)
python scripts/etl_vitals_datasets.py --from-fixtures
```

Saída: `data/processed/vitals/train_rows.csv` e `train_features.csv`
(gitignored; ver README em `data/processed/vitals/`). Seed default: `20260721`.

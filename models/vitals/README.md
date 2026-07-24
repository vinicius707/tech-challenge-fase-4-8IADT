# Modelos de vitais (Isolation Forest)

Artefato **pequeno versionado** para o backend `isolation_forest` /
`hybrid` do `VitalsAnomalyEngine` ([ADR 0029](../../docs/adr/0029-vitais-ml-hibrido.md)).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

| Arquivo | Função |
| ------- | ------ |
| `isolation_forest.joblib` | IsolationForest sklearn + metadata (`feature_columns`, `seed`) |

## Regenerar

Na raiz do repo (com deps do backend):

```bash
# Preferencial: processados do ETL (T9.1)
python scripts/etl_vitals_datasets.py --from-fixtures
cd backend && uv run python ../scripts/train_vitals_if.py

# Ou só fixtures (sem data/processed)
cd backend && uv run python ../scripts/train_vitals_if.py --from-fixtures
```

Seed default: `20260721`. Pesos de autoencoder PyTorch (Épico 9.3) **não**
entram aqui / não rodam no worker.

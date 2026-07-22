# Fixtures de prescrições (sintéticos)

CSVs **sintéticos e versionados** para TDD, demo e runtime da modalidade
`prescriptions` do Limen. Não contêm PHI nem material clínico real.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> Anomalias derivadas destas fixtures são demonstração — **sem** decisão
> terapêutica.

## Calibração

| Campo | Valor |
| ----- | ----- |
| Versão | `2026-07-21.1` |
| Script | `python scripts/prepare_prescription_fixtures.py` (na raiz do repo) |
| Formato | CSV UTF-8, header fixo, `lineterminator=\n` |
| Seed | `20260721` (cenários fixos no script) |

### SHA-256 (bit-a-bit)

| Arquivo | SHA-256 |
| ------- | ------- |
| `prescriptions_normal.csv` | `53b74290bb30ab8102e36a29a75f291bab9cceb106e2293645a7f742e01861b1` |
| `prescriptions_medium.csv` | `61efe84d9207df77d243ffa76c00b661a53b50f911123414babbf4e6170273ad` |
| `prescriptions_high.csv` | `40bba682668c036494eb677b534f3ef861924579dd5c03492d9ca9d9caf1848d` |
| `manifest.json` | regenerado pelo script (inclui os SHAs e o catálogo) |

## Schema

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `timestamp` | string numérica | offset em horas (zero-pad 4), ordenável |
| `medication` | string | identificador sintético do catálogo Limen |
| `dose_mg` | float | dose em miligramas |
| `interval_hours` | float | intervalo entre tomadas (horas) |
| `label` | `normal` \| `anomaly` | só calibração/validação |

## Cenários

| Arquivo | Cenário | Hint de risco | Intenção |
| ------- | ------- | ------------- | -------- |
| `prescriptions_normal.csv` | `normal` | BAIXO | doses/intervalos dentro do catálogo |
| `prescriptions_medium.csv` | `medium` | MEDIO | dose acima do máx. + intervalo irregular |
| `prescriptions_high.csv` | `high` | ALTO | medicamento inesperado + doses extremas |

Metadados canônicos (inclui **catálogo** de faixas): [`manifest.json`](manifest.json).

## Catálogo sintético (referência — demo)

| Medicamento | dose_mg | interval_hours |
| ----------- | ------- | -------------- |
| `metformin` | 500–2000 | 12 |
| `amlodipine` | 5–10 | 24 |
| `losartan` | 25–100 | 24 |

Faixas são **demonstração** (ADR 0010), não formulário hospitalar.

## Catálogo de fontes (referência — não usados em runtime)

| Papel | Fonte | URL / nota |
| ----- | ----- | ---------- |
| Schema / faixas demo | Catálogo sintético Limen | neste README / `manifest.json` |
| Referência acadêmica | Formulários / bulas genéricas públicas | só calibração — **sem** PHI |

Brutos externos (se baixados) ficam em `data/raw/` (gitignored). O CI e a API
**não** dependem desses downloads.

## Regenerar

```bash
python scripts/prepare_prescription_fixtures.py
```

A saída deve coincidir bit-a-bit com os SHA-256 acima / no `manifest.json`.
Spec: [`specs/epic-06-modalidades/03-prescricoes-seed.md`](../../../specs/epic-06-modalidades/03-prescricoes-seed.md).

# Núcleo Caso + fila — Datasets e fixtures de vitais

## Objetivo

Definir o contrato de dados sintéticos de sinais vitais do Limen: catálogo de
datasets públicos usados só para calibração/EDA, fixtures versionadas no
repositório para runtime/TDD/demo, e o caminho documentado para regenerá-las.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 21 de julho de 2026** (T3.0 spec + T3.1 fixtures/script/notebook).

- Fixtures `vitals_normal` / `vitals_medium` / `vitals_high` versionadas.
- `scripts/calibrate_vitals.py` regenera de forma bit-a-bit estável.
- Notebook EDA em `notebooks/eda_vitals_inicial.ipynb`.
- Testes de contrato em `backend/tests/test_vitals_fixtures.py`.

## Escopo

- Catálogo canônico dos datasets de referência para vitais (URLs/slugs).
- Calibração offline das faixas fisiológicas e anomalias injetáveis.
- Geração de fixtures sintéticas em `data/fixtures/vitals/`.
- Notebook EDA inicial em `notebooks/` (exploratório; não roda no CI).
- Script documentado para regenerar fixtures (`scripts/calibrate_vitals.py` ou
  equivalente).
- README curto em `data/fixtures/vitals/` descrevendo schema, cenários e como
  regenerar.

Ficam fora desta etapa: download obrigatório de datasets no CI ou no runtime da
API; PHI real; PhysioNet como dependência de execução; AnomalyEngine/Fusion;
POST de Caso; outbox/RQ; Artefatos MinIO; Alertas; frontend.

## ADRs aplicáveis

- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md):
  runtime e testes usam séries sintéticas; datasets públicos são referência
  metodológica, não dependência crítica.
- [ADR 0001 — Privacidade do Paciente](../../docs/adr/0001-privacidade-paciente.md):
  fixtures não carregam CPF, nome civil nem prontuário real.

## Catálogo de datasets (calibração / relatório)

| Papel | Dataset | URL |
| ----- | ------- | --- |
| Primário (CSV Kaggle) | Human vital signs | https://www.kaggle.com/datasets/engrarri21/human-vital-signs |
| Eventos (opcional) | Patient Vital Signs and Event Tracking | https://www.kaggle.com/datasets/parmajha/patient-vital-signs-and-event-tracking |
| Deterioração | Hospital Deterioration | https://www.kaggle.com/datasets/tarekmasryo/hospital-deterioration-dataset · https://huggingface.co/datasets/tarekmasryo/hospital-deterioration-dataset · https://github.com/tarekmasryo/hospital-deterioration-dataset |

Brutos grandes ficam fora do Git (`.gitignore`). O relatório/notebook cita URL e
passos de obtenção; o CI **não** baixa esses brutos.

## Layout no repositório

```text
data/fixtures/vitals/          # CSV/JSON sintéticos versionados (pequenos)
data/fixtures/vitals/README.md # schema + cenários + regeneração
notebooks/                     # EDA inicial (não é gate de CI)
scripts/calibrate_vitals.py    # regenera fixtures a partir de parâmetros
```

## Schema mínimo das fixtures

Cada fixture de vitais deve permitir ao Épico 3 (spec `03`) alimentar o
AnomalyEngine sem ambiguidade. Campos mínimos por série:

| Campo | Tipo | Notas |
| ----- | ---- | ----- |
| `timestamp` | ISO-8601 ou offset em segundos | ordenável |
| `heart_rate` | number | bpm |
| `spo2` | number | % |
| `systolic_bp` | number | mmHg (opcional se a fixture for mínima) |
| `diastolic_bp` | number | mmHg (opcional) |
| `respiratory_rate` | number | rpm (opcional) |
| `label` | string opcional | ex.: `normal`, `anomaly` — só para validação de calibração |

Cenários mínimos versionados (nomes sugeridos):

- `vitals_normal.csv` — dentro das faixas calibradas; esperado Risco BAIXO.
- `vitals_medium.csv` — anomalias moderadas; esperado Risco MEDIO.
- `vitals_high.csv` — anomalias severas; esperado Risco ALTO.

Os limiares numéricos exatos do Risco ficam na spec `03-caso-vitais-risco.md`;
aqui basta que as fixtures sejam **reprodutíveis** e alinhadas a esses três
níveis na calibração documentada no README das fixtures.

## Calibração

1. Obter (fora do CI) os datasets do catálogo.
2. Explorar faixas e padrões de deterioração no notebook EDA.
3. Fixar parâmetros sintéticos (médias, desvios, janelas de anomalia) no script.
4. Regenerar `data/fixtures/vitals/*` e atualizar o README das fixtures com a
   data/versão da calibração e hashes ou tamanhos esperados.

## Cenários de aceitação

### Cenário 1 — Fixtures versionadas presentes

**Dado** o repositório clonado sem download externo  
**Quando** um desenvolvedor inspecionar `data/fixtures/vitals/`  
**Então** devem existir ao menos as três fixtures `normal` / `medium` / `high`  
**E** um README descrevendo schema, origem metodológica e como regenerar.

### Cenário 2 — Runtime sem Kaggle/HuggingFace

**Dado** a API e os testes do Épico 3  
**Quando** executados em CI ou local sem credenciais de dataset  
**Então** devem consumir apenas `data/fixtures/vitals/`  
**E** não devem falhar por ausência de download de brutos.

### Cenário 3 — Regeneração documentada

**Dado** o script de calibração e seus parâmetros versionados  
**Quando** um mantenedor regenerar as fixtures conforme o README  
**Então** o resultado deve ser bit-a-bit estável ou semanticamente equivalente
documentado (mesmos cenários e faixas)  
**E** o notebook EDA deve existir como evidência exploratória (fora do CI).

### Cenário 4 — Sem PHI

**Dado** qualquer fixture em `data/fixtures/vitals/`  
**Quando** o conteúdo for inspecionado  
**Então** não deve haver CPF, nome civil, prontuário ou identificadores reais
de paciente.

## Critérios de pronto (DoD desta spec / T3.1)

- [x] `data/fixtures/vitals/` com cenários normal/medium/high e README.
- [x] Script de regeneração e notebook EDA inicial commitados.
- [x] Catálogo de URLs espelhado no README das fixtures (e alinhado ao plano).
- [x] Cenários 1–4 acima verificáveis sem download externo no CI.

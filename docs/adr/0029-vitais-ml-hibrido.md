# Vitais: Isolation Forest em runtime + autoencoder PyTorch só evidência

Estende [ADR 0008](0008-vitais-sinteticos.md) sem abandonar fixtures sintéticas no
caminho crítico: o runtime do Caso continua aceitando CSVs no schema Limen;
datasets públicos (Kaggle Human vital signs + amostra Hospital Deterioration)
entram via **ETL offline** (`data/raw/` gitignored → features / fixtures de
treino). PhysioNet permanece **citação metodológica** no relatório — sem
download obrigatório em CI, smoke ou demo ao vivo.

**Produção (worker / API):** `VitalsAnomalyEngine` passa a aceitar
`LIMEN_VITALS_BACKEND` ∈ {`thresholds`, `isolation_forest`, `hybrid`}.

- `thresholds` — comportamento atual (limiares HR/SpO2); **default no CI**.
- `isolation_forest` — score sklearn (`joblib`) carregado de artefato pequeno
  versionado em `models/vitals/`.
- `hybrid` — limiares **OU** score IF (mais sensível; Compose local / demo).

Artefato IF: modelo **pequeno no Git** para `git clone` + `hybrid` sem passo
opaco; treino full documentado em script/notebook para quem tiver brutos em
`data/raw/`.

**Evidência / portfólio (fora do worker):** notebook com **autoencoder PyTorch**
(epochs, loss, early stopping) + **export opcional de pesos**. O runtime
**não** carrega Torch nem pesos do AE — evita vazamento de DL para a imagem
Docker slim e para o CI.

Comparação limiares vs IF vs AE, métricas em holdout, emenda ao
`docs/relatorio-fase4.md` e ao `docs/demo/roteiro-video.md` fazem parte do
Épico 9 (specs), não desta ADR isolada.

## Alternativas rejeitadas

| Alternativa | Motivo |
| ----------- | ------ |
| Download de dataset ao vivo na demo/API | Frágil (rede, licença, tamanho); fora do desenho ADR 0008 / E8 |
| Substituir limiares sem flag | Quebra reprodutibilidade do pytest/smoke atuais |
| AE / PyTorch no worker ou na imagem backend | Infla Docker; risco de “vazamento” DL para produção da demo |
| TensorFlow/Keras para o AE | Footprint maior; menos alinhado ao default de portfólio atual |
| MLP sklearn como AE principal no notebook | Dilui narrativa de epochs/DL; sklearn fica no IF de runtime |
| Fine-tune YOLO / ML de áudio neste épico | Fora do escopo; vitais primeiro |
| PhysioNet como dependência de treino/runtime | Setup/licença pesados; mantido só como citação |

## Relação com ADR 0008

ADR 0008 continua válida: **fixtures sintéticas** alimentam TDD, smoke e demo
reproduzível. Esta ADR adiciona um **segundo trilho opcional** (ETL + IF) e um
**trilho de evidência** (AE), sem tornar Kaggle/PhysioNet dependência do
caminho crítico.

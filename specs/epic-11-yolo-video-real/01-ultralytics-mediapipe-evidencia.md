# Épico 11 — Vídeo real (YOLOv8 + MediaPipe)

## Objetivo

Substituir os stubs sintéticos do Épico 6.1 pelo caminho **real** opt-in de
vídeo: **Detecção em Cena** com YOLOv8 pré-treinado COCO (`ultralytics`) e
**Análise Postural** com MediaPipe Pose, reutilizando o seam de upload / fila
`video` / frames no MinIO / fusão de Risco — sem quebrar o CI offline
(`LIMEN_YOLO_BACKEND=synthetic`, `LIMEN_POSE_BACKEND=synthetic`).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> Detecção em Cena e Análise Postural são demonstração de visão computacional —
> sem fine-tune clínico e sem afirmação de análise cirúrgica (ex.: sangramento).

## Status da entrega

**T11.0 concluída** (spec SDD + índice / ponte E6.1). Implementação T11.1+ em
sessões seguintes nesta branch.

Relação com E6.1: o Épico 6.1 permanece **Concluída** (seam: fixtures AVI,
upload, fila `video`, Pose/Scene engines com backend `synthetic`, frames
anotados, fusão). Este épico entrega o caminho **real** atrás do mesmo seam
(ADR 0030 / 0007).

Ordem das frentes de IA real: **Épico 10 (feito) → Épico 11 (este) → Épico 9
(Vitais ML)**. O Épico 9 tem specs prontas; **implementação não iniciada**.

## Escopo

- Backend **YOLOv8** real via `ultralytics` quando
  `LIMEN_YOLO_BACKEND=ultralytics` (default CI: `synthetic`).
- Backend **MediaPipe Pose** real quando `LIMEN_POSE_BACKEND=mediapipe`
  (default CI: `synthetic`).
- Mesmo contrato de saída do E6.1: `ModalityRisk` + Anomalias + frames anotados
  (`video_frame` no MinIO); kind `pose` vs `scene` inalterado (heurística de
  nome do Artefato / fixture).
- Heurísticas de Detecção em Cena preservadas (ADR 0007): `person_present`,
  `generic_object_present` (proxy COCO `bottle`), `scene_occupied` — sem
  classes clínicas novas.
- Análise Postural real: keypoints → ângulos/estabilidade no mesmo formato de
  Anomalias do engine sintético (contrato agnóstico de backend — ADR 0030).
- Degradação independente: falha/ausência de Ultralytics não impede Pose
  (`mediapipe` ou `synthetic`); falha de MediaPipe não impede Scene
  (`ultralytics` ou `synthetic`).
- Extras opcionais no backend: `uv sync --extra ultralytics` e
  `--extra mediapipe` (Torch/MediaPipe **não** entram na imagem da API; só no
  `worker-video` quando o Compose ligar o extra — ADR 0030).
- TDD: engines reais **injetáveis** (sem download de pesos / sem MediaPipe no
  CI); regressão E6.1 com backends `synthetic`.
- Evidência: `scripts/gerar-evidencia-video.sh` → `data/evidencia/video/`
  (JSON de detecções/keypoints + amostra de frames anotados ou metadados);
  `gerar-evidencia-real.sh` passa a chamar áudio (E10) **e** vídeo (E11).
- `.env.example` / README documentam `LIMEN_YOLO_BACKEND` e
  `LIMEN_POSE_BACKEND` (já existem; fechar textos E11).

Ficam fora desta etapa: Isolation Forest / AE (Épico 9); fine-tune YOLO;
detecção de sangramento ou claim clínico cirúrgico; OpenPose; UI nova de
frames; Exactly-once; Prometheus; job CI com GPU/pesos obrigatórios; download
obrigatório de datasets no CI; trocar fixtures AVI sintéticas do CI por clips
reais (clips “reais” só na evidência local, se usados).

## ADRs aplicáveis

- [ADR 0030 — IA real opt-in + evidência](../../docs/adr/0030-ia-real-opt-in-evidencia.md)
- [ADR 0007 — Escopo vídeo fisio + cirurgia leve](../../docs/adr/0007-escopo-video-fisio-cirurgia-leve.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0020 — Filas `video` / `default`](../../docs/adr/0020-filas-separadas-video.md)
- [ADR 0017 — Timeouts por modalidade](../../docs/adr/0017-timeouts-por-modalidade.md)
- Spec seam: [`../epic-06-modalidades/01-video-pose-yolo.md`](../epic-06-modalidades/01-video-pose-yolo.md)

## Contrato de configuração

| Variável | Função | Default CI |
| -------- | ------ | ---------- |
| `LIMEN_YOLO_BACKEND` | `synthetic` \| `ultralytics` (Detecção em Cena) | `synthetic` |
| `LIMEN_POSE_BACKEND` | `synthetic` \| `mediapipe` (Análise Postural) | `synthetic` |

Sem o extra instalado com backend real → **falha explícita** (`RuntimeError`)
daquele kind, com mensagem clara, sem inventar detecções (fechado na T11.1
para YOLO; T11.2 para MediaPipe).

## Regras de domínio (rascunho — fechar no grilling se necessário)

1. **Kind** `pose` vs `scene` continua determinado pelo Artefato/fixture (E6.1),
   não pelo backend.
2. Campo `backend` no resultado expõe a origem efetiva (`synthetic` |
   `ultralytics` | `mediapipe`).
3. Contrato de Anomalias/score é **agnóstico de backend** (ADR 0030): testes do
   sintético continuam válidos para o real quando o formato bate.
4. Ultralytics usa pesos pré-treinados COCO (`yolov8n.pt` ou equivalente leve);
   **sem** fine-tune neste épico.
5. Evidência de vídeo versionada neste épico; orquestrador real acumula E10+E11.

## Cenários de aceitação

### Cenário 1 — CI / regressão E6.1

**Dado** `LIMEN_YOLO_BACKEND=synthetic` e `LIMEN_POSE_BACKEND=synthetic` (CI)  
**Quando** `uv run pytest` e processar fixtures `video_physio` /
`video_surgery_light`  
**Então** engines sintéticos rodam sem Ultralytics/MediaPipe instalados  
**E** testes E6.1 existentes continuam verdes.

### Cenário 2 — Detecção em Cena real (injetável no TDD; Ultralytics na evidência)

**Dado** `LIMEN_YOLO_BACKEND=ultralytics` e detector injetado (ou SDK real)  
**Quando** processar fixture/cena `surgery_light`  
**Então** `backend=ultralytics`, heurísticas COCO avaliadas  
**E** frames anotados persistem no MinIO  
**E** modalidade `video` contribui ao Risco.

### Cenário 3 — Análise Postural real (injetável no TDD; MediaPipe na evidência)

**Dado** `LIMEN_POSE_BACKEND=mediapipe` e estimador injetado (ou SDK real)  
**Quando** processar fixture/cena `physio`  
**Então** `backend=mediapipe`, Anomalias de estabilidade/ângulo no contrato E6.1  
**E** frames anotados no MinIO.

### Cenário 4 — Degradação independente

**Dado** YOLO real indisponível e Pose `synthetic` (ou o inverso)  
**Quando** processar o kind correspondente  
**Então** só o kind com backend quebrado falha (ou degrada conforme regra
fechada na implementação)  
**E** o outro kind / backend permanece utilizável  
**E** falha parcial do Caso (ADR 0013) continua válida.

### Cenário 5 — Opt-in sem afetar API leve

**Dado** Compose/API sem extras Torch/MediaPipe  
**Quando** CI e smoke padrão  
**Então** imagem da API não exige Ultralytics/MediaPipe  
**E** `worker-video` só carrega extras quando o env real estiver ligado
(documentado).

### Cenário 6 — Evidência commitada

**Dado** extras instalados localmente e fixtures de vídeo  
**Quando** `./scripts/gerar-evidencia-video.sh`  
**Então** artefatos em `data/evidencia/video/` prontos para commit  
**E** `./scripts/gerar-evidencia-real.sh` chama evidência de áudio (E10) e de
vídeo (E11).

## Tarefas planejadas (uma por commit)

| Tarefa | Conteúdo |
| ------ | -------- |
| T11.0 | Esta spec + notas de índice / ponte E6.1 (docs) — **feita** |
| T11.1 | Env + YOLOv8 Ultralytics injetável + TDD (scene) — **feita** |
| T11.2 | MediaPipe Pose injetável + TDD (pose) — **feita** |
| T11.3 | Wiring worker-video / extras Compose + degradação independente — **feita** |
| T11.4 | `gerar-evidencia-video.sh` + orquestrador real (E10+E11) |
| T11.5 | Fechamento docs (README, `.env.example`, índice) |

Branch: `feature/limen-epic-11-yolo-video-real` a partir de `main`.

## Critérios de pronto (DoD E11)

- [x] Spec SDD aprovada (esta) + docs da T11.0.
- [ ] YOLO + MediaPipe reais opt-in; TDD sem pesos/rede no CI.
- [ ] Regressão E6.1 com `synthetic`; contrato de saída estável.
- [ ] Degradação independente Pose ↔ Scene.
- [ ] Evidência em `data/evidencia/video/` via script versionado; orquestrador
      inclui vídeo.
- [ ] `.env.example` / README / índice atualizados.
- [ ] Sem fine-tune; sem claim clínico; sem Épico 9; sem UI nova.

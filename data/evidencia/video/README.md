# Evidência de vídeo (IA real opt-in)

Artefatos JSON gerados por `./scripts/gerar-evidencia-video.sh` (ADR 0030).

| Arquivo | Conteúdo |
| ------- | -------- |
| `analysis.json` | Metadados + Pose + Scene + risco |
| `pose.json` | Análise Postural (stability / Anomalias / frames) |
| `scene.json` | Detecção em Cena (COCO / heurísticas / frames) |

Fixtures de entrada: `data/fixtures/video/video_physio.avi` (pose) e
`video_surgery_light.avi` (scene / surgery).

## Gerar

```bash
# Sem Ultralytics/MediaPipe (formato / CI)
./scripts/gerar-evidencia-video.sh --dry-run

# Com extras instalados + backends reais no .env
./scripts/gerar-evidencia-video.sh
```

Orquestrador (E10 áudio + E11 vídeo): `./scripts/gerar-evidencia-real.sh`.

Commite a saída **live** antes da entrega à banca. Dry-run marca `"mode": "dry-run"`.

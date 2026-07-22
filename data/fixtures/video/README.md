# Fixtures de vídeo (sintéticos)

Clips **sintéticos e versionados** (AVI RGB24) para TDD, demo e runtime da
modalidade `video` do Limen. Não contêm PHI nem material clínico real.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> A cena “cirurgia leve” é apenas proxy visual para Detecção em Cena — **sem**
> dataset de sangramento e **sem** afirmação de análise clínica.

## Calibração

| Campo | Valor |
| ----- | ----- |
| Versão | `2026-07-21.1` |
| Script | `python scripts/prepare_video_fixtures.py` (na raiz do repo) |
| Resolução | 64×48, 12 frames @ 4 fps |
| Seed | `20260721` (geometria determinística no script) |
| Container | AVI não comprimido (`DIB ` / BGR24) |

### SHA-256 (bit-a-bit)

| Arquivo | SHA-256 |
| ------- | ------- |
| `video_physio.avi` | `d08fefaaeb2450888e418f773fd14912f88253ed0a202b2fe6b4b5533f1bafac` |
| `video_surgery_light.avi` | `1859400287d3aa6f9b2f9b8cf1b52d74648d3de15a1cd89985eee2ac54d6bfb2` |
| `manifest.json` | regenerado pelo script (inclui os SHA dos clips) |

## Cenários

| Arquivo | Cenário | Análise alvo (E6.1) |
| ------- | ------- | ------------------- |
| `video_physio.avi` | `physio` | Análise Postural (MediaPipe Pose) |
| `video_surgery_light.avi` | `surgery_light` | Detecção em Cena (YOLOv8 COCO + heurísticas) |

Metadados canônicos: [`manifest.json`](manifest.json).

## Catálogo de fontes (referência — não usados em runtime)

| Papel | Fonte | URL |
| ----- | ----- | --- |
| Fisio / postura | 3DYoga90 (ou gravação própria 30–60s) | https://github.com/seonokkim/3dyoga90 |
| Cirurgia leve | Stock / material sob Creative Commons (CC0) | https://creativecommons.org/publicdomain/zero/1.0/ |

Brutos grandes (se baixados localmente) ficam em `data/raw/` (gitignored).
O CI e a API **não** dependem desses downloads: as fixtures sintéticas bastam
para TDD até a demo.

Exemplos de stock CC usáveis na demo (substituir/regenerar fora do CI se
quiser clip “real”):

- Busca genérica por “operating room” / “surgery” em bancos CC0 (ex.:
  [Pexels](https://www.pexels.com/), [Pixabay](https://pixabay.com/)) —
  documentar a URL escolhida no relatório da Fase 4.

## Regenerar

```bash
python scripts/prepare_video_fixtures.py
```

A saída deve coincidir com os SHA-256 dos clips acima. Spec:
[`specs/epic-06-modalidades/01-video-pose-yolo.md`](../../../specs/epic-06-modalidades/01-video-pose-yolo.md).

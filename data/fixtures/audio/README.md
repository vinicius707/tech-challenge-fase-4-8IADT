# Fixtures de áudio (sintéticos)

Clips **sintéticos e versionados** (WAV PCM S16LE mono) para TDD, demo e
runtime da modalidade `audio` do Limen. Não contêm PHI nem material clínico
real.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> Transcrições/escores derivados destas fixtures são demonstração — **sem**
> diagnóstico clínico.

## Calibração

| Campo | Valor |
| ----- | ----- |
| Versão | `2026-07-21.1` |
| Script | `python scripts/prepare_audio_fixtures.py` (na raiz do repo) |
| Formato | WAV PCM 16-bit little-endian, mono, 8 kHz |
| Duração | 2,0 s (≤ **60 s** exigidos pela spec E6.2) |
| Seed | `20260721` (geometria/tom determinísticos no script) |

### SHA-256 (bit-a-bit)

| Arquivo | SHA-256 |
| ------- | ------- |
| `audio_speech.wav` | `5b161a0f7c29b9db73681ae94c146105c5b2f6c87c7cb5187102d47da3c2773a` |
| `manifest.json` | regenerado pelo script (inclui o SHA do clip) |

## Cenários

| Arquivo | Cenário | Uso (E6.2) |
| ------- | ------- | ---------- |
| `audio_speech.wav` | `speech` | Upload + analyzer local / Azure injetável / cache |

Metadados canônicos: [`manifest.json`](manifest.json).

## Catálogo de fontes (referência — não usados em runtime)

| Papel | Fonte | URL |
| ----- | ----- | --- |
| Speech / ambient | AudioSet | https://research.google.com/audioset/ |
| Utterance médica | Medical Speech / gravação própria ≤60s (CC) | documentar URL escolhida no relatório da Fase 4 |

Brutos grandes (se baixados localmente) ficam em `data/raw/` (gitignored).
O CI e a API **não** dependem desses downloads: a fixture sintética basta
para TDD até a demo.

## Regenerar

```bash
python scripts/prepare_audio_fixtures.py
```

A saída deve coincidir bit-a-bit com o SHA-256 do clip no `manifest.json`.
Spec: [`specs/epic-06-modalidades/02-audio-azure.md`](../../../specs/epic-06-modalidades/02-audio-azure.md).

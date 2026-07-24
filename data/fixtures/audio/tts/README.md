# Fixtures TTS pt-BR (Épico 10 / T10.5)

Áudios gerados com TTS macOS (`say` voz Luciana) + `afconvert`, ≤60 s,
16 kHz mono PCM. Usados como entrada de `scripts/gerar-evidencia-audio.sh`.

> Demonstração acadêmica — sem PHI nem diagnóstico.

## Arquivos

| Arquivo | Cenário |
| ------- | ------- |
| `audio_tts_neutra.wav` | Consulta sem Termos Críticos |
| `audio_tts_critica.wav` | Queixas com Termos Críticos (`dor no peito`, `falta de ar`) |
| `manifest.json` | SHA-256 + roteiros |

## Regenerar (macOS)

```bash
python scripts/prepare_tts_audio_fixtures.py
```

Spec: [`specs/epic-10-azure-audio-real/01-speech-language-evidencia.md`](../../../../specs/epic-10-azure-audio-real/01-speech-language-evidencia.md).

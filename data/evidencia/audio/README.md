# Evidência de áudio (IA real opt-in)

Artefatos JSON gerados por `./scripts/gerar-evidencia-audio.sh` (ADR 0030).

| Arquivo | Conteúdo |
| ------- | -------- |
| `analysis.json` | Metadados + Transcrição + Sentimento + Termos + risco |
| `transcript.json` | Transcrição |
| `sentiment.json` | Sentimento / key phrases |
| `critical_terms.json` | Termos Críticos locais |

## Gerar

```bash
# Sem Azure (formato / CI)
./scripts/gerar-evidencia-audio.sh --dry-run

# Com credenciais F0 no .env
./scripts/gerar-evidencia-audio.sh
```

Orquestrador (E10 áudio + E11 vídeo): `./scripts/gerar-evidencia-real.sh`.

Commite a saída **live** antes da entrega à banca. Dry-run marca `"mode": "dry-run"`.

# Roteiro de vídeo — demo Limen (Fase 4)

> Protótipo acadêmico — **não** é um dispositivo médico.

**Duração-alvo:** 4–6 minutos.  
**Pré-requisitos (antes de gravar):**

```bash
./scripts/start-limen.sh
./scripts/seed-multimodal-demo.sh   # Caso multimodal idempotente
```

Login demo: `medico` / `medico_dev_only` (ou `admin` para DLQ).  
UI: http://localhost:3000 · API docs: http://localhost:8000/docs

## O que NÃO mostrar

- Conteúdo de `.env`, tokens JWT, `PII_ENCRYPTION_KEY`, senhas.
- PHI real (CPF, nome civil, prontuário) — use só o seed sintético.
- Falhas de rede não ensaiadas; abas de DevTools com secrets.
- Afirmações de diagnóstico clínico (“o paciente está em risco real…”).

## Passos cronológicos

| # | Tempo | Ação na tela | Narrar |
| - | ----- | ------------ | ------ |
| 1 | 0:00–0:30 | Tela `/login` | Apresentar o Limen como protótipo multimodal acadêmico (não dispositivo médico). |
| 2 | 0:30–0:50 | Login como `medico` | Papéis JWT; sem PHI. |
| 3 | 0:50–1:20 | Lista/detalhe de Paciente | Código `PAC-NNN`; Rótulo Sensível mascarado; (opcional, 10s) reveal + mencionar auditoria. |
| 4 | 1:20–2:40 | Detalhe do Caso seed | Modalidades vitals/vídeo/áudio/prescriptions; status; Risco fundido; **Justificativa** template. |
| 5 | 2:40–3:20 | Alertas | Feed/região de Alertas; toast `polite` se houver evento; mencionar SSE com Bearer. |
| 6 | 3:20–3:50 | Tema dark/light (toggle) | Acessibilidade / AA nas rotas estrela. |
| 7 | 3:50–4:30 | (Opcional) `/admin/falhas` com `admin` | DLQ ≠ Alertas clínicos; redrive/discard com auditoria. |
| 8 | 4:30–5:30 | Terminal (curto) ou slide | Mencionar `./scripts/smoke-caso-vitais.sh`, publish GHCR em `main`, notebooks e relatório. |
| 9 | 5:30–6:00 | Encerramento | Repetir disclaimer; apontar README + `docs/relatorio-fase4.md`. |

## Dicas de gravação

- Preferir o Caso já processado (`done`) após o seed + workers.
- Se o Risco ainda estiver `processing`, esperar ou cortar e retomar.
- Resolução ≥ 1280×720; tipografia legível; não cobrir o brand Limen no hero do login.
- Áudio limpo; citar URLs de datasets só se couber no tempo (detalhe no relatório).

## Checklist pós-gravação

- [ ] Disclaimer dito no início e no fim
- [ ] Nenhum secret visível
- [ ] Caso multimodal ou pelo menos vitais + Justificativa/Alertas
- [ ] Link/repo mencionado (README / relatório)

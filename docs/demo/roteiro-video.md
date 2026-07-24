# Roteiro de vídeo — demo Limen (Fase 4)

> Protótipo acadêmico — **não** é um dispositivo médico.

**Duração-alvo:** 5–7 minutos (~90% app multimodal, ~10% notebook ML).  
**Pré-requisitos (antes de gravar):**

```bash
# Demo com vitais híbridos (limiares OU Isolation Forest) — sem download de dataset
export LIMEN_VITALS_BACKEND=hybrid   # ou no .env local
./scripts/start-limen.sh
./scripts/seed-multimodal-demo.sh   # Caso multimodal idempotente
```

Login demo: `medico` / `medico_dev_only` (ou `admin` para DLQ).  
UI: http://localhost:3000 · API docs: http://localhost:8000/docs

**Não baixe** Kaggle/PhysioNet/HuggingFace durante a gravação — fixtures e o
modelo IF já estão no repo (`data/fixtures/`, `models/vitals/`).

## O que NÃO mostrar

- Conteúdo de `.env`, tokens JWT, `PII_ENCRYPTION_KEY`, senhas.
- PHI real (CPF, nome civil, prontuário) — use só o seed sintético.
- Falhas de rede não ensaiadas; abas de DevTools com secrets.
- Afirmações de diagnóstico clínico (“o paciente está em risco real…”).
- Download ao vivo de datasets (fora do escopo da demo).

## Passos cronológicos

| # | Tempo | Ação na tela | Narrar |
| - | ----- | ------------ | ------ |
| 1 | 0:00–0:30 | Tela `/login` | Apresentar o Limen como protótipo multimodal acadêmico (não dispositivo médico). |
| 2 | 0:30–0:50 | Login como `medico` | Papéis JWT; sem PHI. |
| 3 | 0:50–1:20 | Lista/detalhe de Paciente | Código `PAC-NNN`; Rótulo Sensível mascarado; (opcional, 10s) reveal + mencionar auditoria. |
| 4 | 1:20–2:50 | Detalhe do Caso seed | Modalidades vitals/vídeo/áudio/prescriptions; status; Risco fundido; **Justificativa** template. Mencionar `LIMEN_VITALS_BACKEND=hybrid` (limiares OU IF). |
| 5 | 2:50–3:30 | Alertas | Feed/região de Alertas; toast `polite` se houver evento; mencionar SSE com Bearer. |
| 6 | 3:30–4:00 | Tema dark/light (toggle) | Acessibilidade / AA nas rotas estrela. |
| 7 | 4:00–4:30 | (Opcional) `/admin/falhas` com `admin` | DLQ ≠ Alertas clínicos; redrive/discard com auditoria. |
| 8 | 4:30–5:20 | Terminal (curto) | `./scripts/smoke-caso-vitais.sh`, publish GHCR em `main`, CI em `thresholds`. |
| 9 | 5:20–6:10 | Notebook (curto, ~10%) | Abrir `notebooks/compare_vitals_ml.ipynb` ou curva de loss em `train_vitals_autoencoder.ipynb` — AE **só evidência**, fora do worker. |
| 10 | 6:10–6:40 | Encerramento | Repetir disclaimer; apontar README + `docs/relatorio-fase4.md` (ADR 0029). |

## Dicas de gravação

- Preferir o Caso já processado (`done`) após o seed + workers.
- Se o Risco ainda estiver `processing`, esperar ou cortar e retomar.
- Resolução ≥ 1280×720; tipografia legível; não cobrir o brand Limen no hero do login.
- Áudio limpo; URLs de datasets ficam no relatório — **não** baixar na live.

## Checklist pós-gravação (“pronto para gravar” / revisão)

- [ ] Disclaimer dito no início e no fim
- [ ] Nenhum secret visível
- [ ] Caso multimodal ou pelo menos vitais + Justificativa/Alertas
- [ ] `hybrid` (ou menção a `LIMEN_VITALS_BACKEND`) narrado sem download de dataset
- [ ] Trecho curto de notebook (comparação ou AE) — AE explícito como evidência
- [ ] Link/repo mencionado (README / relatório §5.3 Vitais ML)

# Performance (Limen)

Artefatos e regras de Lighthouse do shell frontend.

| Caminho | Papel |
| ------- | ----- |
| [`baseline/`](baseline/) | Baseline versionada (Épico 4); só atualizar em commit explícito |
| [`baseline/summary.json`](baseline/summary.json) | Scores máquina-legíveis usados pelo gate |
| `check/` | Saída local do modo `--check` (gitignored) |
| [`../../scripts/lighthouse-gate.mjs`](../../scripts/lighthouse-gate.mjs) | Pisos absolutos + tolerância de regressão |
| [`../../scripts/lighthouse-baseline.mjs`](../../scripts/lighthouse-baseline.mjs) | Medição (`baseline` ou `--check`) |

## Gate (E7.3)

- **Absolutos (desktop):** Perf ≥90, A11y ≥95, Best Practices ≥90.
- **Regressão:** tolerância de **2** pontos vs baseline.
- **Piso efetivo:** `max(absoluto, baseline − 2)` quando o baseline já está
  ≥ absoluto; se o baseline versionado ainda estiver abaixo do absoluto (hoje:
  `/login` Perf 88), o piso é só `baseline − 2` até um commit explícito de novo
  baseline.
- **Rotas gate:** `/login`, `/pacientes`.
- **SEO:** só relatório; fora do gate.
- **CI:** job `Lighthouse gate` em [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
  — `npm run build` + `npm start`, depois `npm run lighthouse:check` com
  `LIMEN_LH_RUNS=3` (mediana); artefatos em `docs/perf/check/` (upload no
  Actions). Baseline versionada permanece intocada pelo job.

Detalhes e regeneração: [`baseline/README.md`](baseline/README.md).

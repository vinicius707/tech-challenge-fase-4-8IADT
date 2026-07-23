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
- **Regressão:** falha se score &lt; baseline − **2** (ou &lt; absoluto — o mais
  restritivo).
- **Rotas gate:** `/login`, `/pacientes`.
- **SEO:** só relatório; fora do gate.
- **CI:** job de gate na T7.13 (esta pasta documenta a regra compartilhada com o
  script local).

Detalhes e regeneração: [`baseline/README.md`](baseline/README.md).

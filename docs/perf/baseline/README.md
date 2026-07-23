# Baseline Lighthouse — shell Limen

Baseline versionada de performance / a11y / best-practices / SEO do shell
Limen. O **gate por regressão** (Épico 7 / E7.3) compara um run novo a este
diretório — não sobrescreve estes artefatos no modo `check`.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Metadados

| Campo | Valor |
| ----- | ----- |
| Data (UTC) | 2026-07-22T00:21:53.781Z |
| Commit (SHA curto) | `8873403` |
| Ambiente | desktop (Lighthouse `formFactor: desktop`, 1350×940) |
| URL base | `http://127.0.0.1:3000` |
| Build | Next.js production (`npm run build` + `npm start`) |

## Rotas medidas (gate)

| Rota | Artefatos | Perf | A11y | BP | SEO |
| ---- | --------- | ---- | ---- | -- | --- |
| `/login` | `login-desktop.report.{json,html}` | 88 | 100 | 100 | 100 |
| `/pacientes` | `pacientes-desktop.report.{json,html}` | 97 | 100 | 96 | 100 |

Resumo máquina-legível: [`summary.json`](summary.json).

`/pacientes` usa sessão sintética em `localStorage` (`limen-session`) apenas para
passar o AuthGate e medir o shell autenticado — o token não é válido na API.

`/casos/[id]` fica fora do gate até haver sessão sintética estável no CI.

## Gate (absoluto + regressão)

Lógica em [`scripts/lighthouse-gate.mjs`](../../../scripts/lighthouse-gate.mjs):

| Regra | Valor |
| ----- | ----- |
| Performance | ≥ **90** |
| Accessibility | ≥ **95** |
| Best Practices | ≥ **90** |
| SEO | informado no relatório; **fora** do gate |
| Tolerância de regressão | **2** pontos abaixo do baseline |
| Piso efetivo | Se baseline ≥ absoluto: `max(absoluto, baseline − 2)`. Se baseline &lt; absoluto (ex.: login Perf 88): só `baseline − 2` até um novo baseline explícito. |

Falhas listam `rota / categoria`, `score`, `baseline`, `floor` e `delta`.

Atualizar este diretório **somente** em commit explícito de “novo baseline”
(não no modo `check` nem silenciosamente a cada PR).

## Como regenerar (write baseline)

1. Suba o frontend em produção local:

```bash
cd frontend
npm ci
npm run build
npm start -- -H 127.0.0.1 -p 3000
```

2. Em outro terminal:

```bash
cd frontend
npm run lighthouse:baseline
# equivalente: node ../scripts/lighthouse-baseline.mjs
```

Opcional: `LIMEN_BASE_URL=http://127.0.0.1:3000`.

3. Atualize a tabela acima e o SHA em [`summary.json`](summary.json); abra os
   `.report.html` no browser para inspeção.

## Como checar (modo check)

Com o frontend no ar (mesmo pré-requisito):

```bash
cd frontend
npm run lighthouse:check
# equivalente: node ../scripts/lighthouse-baseline.mjs --check
```

- Mede `/login` e `/pacientes` (desktop).
- Escreve artefatos em `docs/perf/check/` (gitignored) — **não** altera
  `docs/perf/baseline/`.
- Exit `0` se todos os scores gated ≥ piso; `1` caso contrário (mensagem com
  rota + categoria + delta).

O mesmo comando roda no CI (job **Lighthouse gate**), com upload dos
relatórios em `docs/perf/check/` como artefato Actions — sem alterar este
diretório `baseline/`.

Dependências de geração (dev): `lighthouse`, `chrome-launcher`, `puppeteer-core`
em `frontend/`. Requer Chrome/Chromium instalado na máquina.

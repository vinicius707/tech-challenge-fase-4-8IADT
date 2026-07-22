# Baseline Lighthouse — Épico 4 (shell)

Baseline versionada de performance / a11y / best-practices / SEO do shell
Limen. **Sem gate de CI** neste épico (comparação futura no Épico 7/8).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Metadados

| Campo | Valor |
| ----- | ----- |
| Data (UTC) | 2026-07-22T00:21:53.781Z |
| Commit (SHA curto) | `8873403` |
| Ambiente | desktop (Lighthouse `formFactor: desktop`, 1350×940) |
| URL base | `http://127.0.0.1:3000` |
| Build | Next.js production (`npm run build` + `npm start`) |

## Rotas medidas

| Rota | Artefatos | Perf | A11y | BP | SEO |
| ---- | --------- | ---- | ---- | -- | --- |
| `/login` | `login-desktop.report.{json,html}` | 88 | 100 | 100 | 100 |
| `/pacientes` | `pacientes-desktop.report.{json,html}` | 97 | 100 | 96 | 100 |

Resumo máquina-legível: [`summary.json`](summary.json).

`/pacientes` usa sessão sintética em `localStorage` (`limen-session`) apenas para
passar o AuthGate e medir o shell autenticado — o token não é válido na API.

## Como regenerar

1. Suba o frontend em produção local:

```bash
cd frontend
npm ci
npm run build
npm start -- -H 127.0.0.1 -p 3000
```

2. Em outro terminal, na raiz do repositório (ou via script npm):

```bash
cd frontend
npm run lighthouse:baseline
# equivalente: node ../scripts/lighthouse-baseline.mjs
```

Opcional: `LIMEN_BASE_URL=http://127.0.0.1:3000`.

3. Atualize a tabela acima e o SHA em [`summary.json`](summary.json) se
   necessário; abra os `.report.html` no browser para inspeção.

Dependências de geração (dev): `lighthouse`, `chrome-launcher`, `puppeteer-core`
em `frontend/`. Requer Chrome/Chromium instalado na máquina.

# Frontend Limen (Épico 4)

Next.js App Router + Tailwind CSS + shadcn/ui. Proxy `/api/*` → FastAPI
(`BACKEND_URL`, padrão `http://localhost:8000`).

> Não é um dispositivo médico.

## Documentação

| Doc | Conteúdo |
| --- | -------- |
| [Guia de uso + prints](../docs/frontend/guia-de-uso.md) | Fluxo login → Paciente → Caso |
| [Troubleshooting](../docs/frontend/troubleshooting.md) | Diagnóstico Compose/UI/API |
| [Baseline Lighthouse](../docs/perf/baseline/) | Scores versionados + gate |
| [Gate Lighthouse](../docs/perf/README.md) | Absoluto + regressão (CI) |

## Subir tudo (recomendado)

Na raiz do repositório:

```bash
./scripts/start-limen.sh
```

## Local (fora do Compose, só UI)

Pré-requisito: backend em `http://localhost:8000` (ou ajuste `BACKEND_URL`).

```bash
cd frontend
npm ci
npm run dev
```

UI: <http://localhost:3000>  
Health via proxy: <http://localhost:3000/api/health>

## Scripts

| Comando | Função |
| ------- | ------ |
| `npm run dev` | Dev server (Turbopack) |
| `npm run build` / `npm start` | Produção |
| `npm test` | Vitest (proxy + auth/sessão) |
| `npm run lint` | ESLint |
| `npm run lighthouse:baseline` | Regenera [`docs/perf/baseline/`](../docs/perf/baseline/) (frontend no ar) |
| `npm run lighthouse:check` | Gate vs baseline (absoluto + regressão; não grava baseline) |

## Variáveis

| Variável | Função |
| -------- | ------ |
| `BACKEND_URL` | Origem do FastAPI para o rewrite (Compose: `http://backend:8000`) |
| `FRONTEND_PORT` | Porta publicada no Compose (padrão `3000`) |

# Frontend Limen (Épico 4)

Next.js App Router + Tailwind CSS + shadcn/ui. Proxy `/api/*` → FastAPI
(`BACKEND_URL`, padrão `http://localhost:8000`).

> Não é um dispositivo médico.

## Local (fora do Compose)

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

## Variáveis

| Variável | Função |
| -------- | ------ |
| `BACKEND_URL` | Origem do FastAPI para o rewrite (Compose: `http://backend:8000`) |
| `FRONTEND_PORT` | Porta publicada no Compose (padrão `3000`) |

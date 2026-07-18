# Frontend: Next.js (App Router) front-only

A UI do Limen usa Next.js com App Router como frontend puro: páginas e Client Components consomem a API FastAPI. Rewrites/proxy de `/api/*` para o backend. Sem Route Handlers como BFF e sem mover motores de IA para Node. Substitui a escolha anterior de Vite SPA. Motivo: routing/layouts modernos mantendo o domínio e a fila no Python.

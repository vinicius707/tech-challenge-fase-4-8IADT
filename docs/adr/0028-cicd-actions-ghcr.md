# CI/CD: GitHub Actions + imagens no GHCR

Pipeline em PR/push: pytest do backend, gate Lighthouse do frontend, build das
imagens Docker `limen-backend` e `limen-frontend`. Push para GitHub Container
Registry **somente em `main`** (tags `main-<sha>` e `latest`); PRs rodam build
sem publish. Imagens: `ghcr.io/<owner>/limen-backend` e
`ghcr.io/<owner>/limen-frontend` (owner em lowercase; `GITHUB_TOKEN` +
`packages: write`).

Smoke de `docker compose`: sobe a stack, espera healthchecks, valida `/health` e
**enfileira um Caso sintético só com vitais** (sem vídeo/Azure), aguardando
status `done`. Script: `scripts/smoke-caso-vitais.sh`. Job CI **Smoke Caso
vitais** (`needs: backend`) em push e PR. `AZURE_ENABLED=false` no CI. E2E
Playwright fica fora do escopo fechado.

Não há deploy automático em cloud; o CD da demo é `docker compose` com imagens
do GHCR. Motivo: validar API + outbox + worker + Postgres/Redis/MinIO antes da
demo, sem YOLO/Azure no pipeline. Alternativas rejeitadas: smoke só `/health`;
E2E UI no CI nesta fase; publish em todo PR; deploy cloud automático.

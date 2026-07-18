# CI/CD: GitHub Actions + imagens no GHCR

Pipeline em PR/push: lint e typecheck do frontend Next, pytest do backend, build das imagens Docker (`backend`, `frontend`). Push para GitHub Container Registry **somente em `main`** (tags `main-<sha>` e `latest`); PRs rodam só CI (lint/test/build sem publish).

Smoke de `docker compose`: sobe a stack, espera healthchecks, valida `/health` e **enfileira um Caso sintético só com vitais** (sem vídeo/Azure), aguardando status `done`. `AZURE_ENABLED=false` no CI. E2E Playwright fica fora do escopo fechado.

Não há deploy automático em cloud; o CD da demo é `docker compose` com imagens do GHCR. Motivo: validar API + outbox + worker + Postgres/Redis/MinIO antes da demo, sem YOLO/Azure no pipeline. Alternativas rejeitadas: smoke só `/health`; E2E UI no CI nesta fase; publish em todo PR; deploy cloud automático.

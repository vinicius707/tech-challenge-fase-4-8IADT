# CI/CD e entrega — Publish GHCR e smoke Caso vitais (E8.1)

## Objetivo

Completar o CD da demo: **publicar imagens** `backend` e `frontend` no GHCR
somente a partir de `main`, e **validar a stack Compose** com um smoke que
enfileira um Caso sintético só com vitais até `done` (`AZURE_ENABLED=false`).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 22 de julho de 2026** (T8.0–T8.4: specs E8.1/E8.2, smoke Caso
vitais local + CI, publish GHCR só em `main`, e fechamento docs do E8.1).

Etapa posterior do Épico 8 (spec própria):

- E8.2 — Seed demo, notebooks finais, relatório, roteiro vídeo e README de
  entrega

## Escopo

- Estender o workflow GitHub Actions existente
  ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)):
  - **Build** das imagens Docker `backend` e `frontend` (Dockerfiles já no
    repo) em PR e em push.
  - **Push para GHCR** (`ghcr.io/<owner>/<image>`) **somente em `main`**, com
    tags `main-<sha>` e `latest`.
  - Em PR / branches que não sejam `main`: build (e testes existentes) **sem**
    publish.
- Smoke Compose de entrega (além do
  [`scripts/smoke-foundation.sh`](../../scripts/smoke-foundation.sh)):
  - Sobe a stack (`docker compose up` com wait/healthchecks).
  - Valida `GET /health` (contrato já da fundação).
  - Autentica com Operador seed (`SEED_MEDICO_*` / equivalente do
    `.env.example`).
  - Cria Paciente (se necessário) e `POST` de Caso com fixture de vitais
    versionada (ex.: `data/fixtures/vitals/vitals_medium.csv`) +
    `Idempotency-Key`.
  - Aguarda o Caso chegar a `status=done` (poll documentado; timeout
    configurável).
  - **Não** envia vídeo/áudio/prescrições; **não** exige Azure.
- Variável `AZURE_ENABLED=false` no ambiente do smoke/CI (já padrão do
  `.env.example`).
- Script reutilizável na raiz (ex.: `scripts/smoke-caso-vitais.sh`), invocável
  localmente e pelo job de CI.
- Documentação mínima do fluxo no README / docs do Épico 8 (fechamento fino
  em T8.4).

Ficam fora desta etapa: E2E Playwright/UI; publish em todo PR; deploy cloud
automático; YOLO/Azure no pipeline; seed multimodal completo, notebooks,
relatório e roteiro de vídeo (E8.2); alterar gates Lighthouse já entregues
(Épico 7).

## ADRs aplicáveis

- [ADR 0028 — CI/CD Actions + GHCR](../../docs/adr/0028-cicd-actions-ghcr.md):
  publish só em `main`; smoke Compose + Caso vitais; sem E2E UI nesta fase.
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md):
  fixture versionada no smoke (sem download de dataset no CI).
- [ADR 0016 — Outbox](../../docs/adr/0016-outbox-leve.md) /
  [ADR 0002 — RQ](../../docs/adr/0002-fila-redis-worker.md): o smoke exercita
  o caminho real outbox → worker → fusão.
- [ADR 0019 — Observabilidade](../../docs/adr/0019-observabilidade.md):
  healthchecks Compose + `/health`.

Nenhuma decisão nova de arquitetura identificada (ADR 0028 já fecha o desenho).

## Contratos de entrega (mínimos)

### Imagens GHCR

| Imagem | Contexto de build | Tags em `main` |
| ------ | ----------------- | -------------- |
| `limen-backend` | `backend/Dockerfile` | `main-<sha>`, `latest` |
| `limen-frontend` | `frontend/Dockerfile` | `main-<sha>`, `latest` |

Registry: `ghcr.io/<owner>/…` (owner em lowercase). Permissões do job:
`packages: write` (e `contents: read`) no job de imagens. Login via
`GITHUB_TOKEN`.

### Smoke Caso vitais

Pré-condições: Compose saudável; Operadores seed disponíveis; fixture CSV de
vitais no repo.

Passos obrigatórios (ordem):

1. `GET /health` → contrato ok (postgres/redis/minio).
2. `POST /auth/login` com credenciais seed → access token.
3. Garantir Paciente (criar via API ou reutilizar seed documentado).
4. `POST /patients/{id}/cases` com CSV vitais + `Idempotency-Key`.
5. Poll `GET /cases/{id}` até `status == "done"` (ou falha com mensagem
   clara se timeout / `failed`).

Critério de sucesso: Caso `done` com modalidade `vitals` concluída; sem
chamada Azure.

## Cenários de aceitação

### Cenário 1 — Publish em `main`

**Dado** um push (ou merge) na branch `main` com CI verde até o job de imagens  
**Quando** o step de publish executar  
**Então** as imagens `backend` e `frontend` existem no GHCR  
**E** possuem tags `main-<sha>` e `latest`  
**E** o job usa credencial de registry sem secrets extras além do
`GITHUB_TOKEN` (ou documenta o secret se inevitável).

### Cenário 2 — PR sem publish

**Dado** um pull request contra `main`  
**Quando** o CI rodar o build das imagens  
**Então** o build completa (ou falha só por erro de Dockerfile/contexto)  
**E** **não** há push de tags `latest` / `main-*` para o GHCR.

### Cenário 3 — Smoke local Caso vitais

**Dado** a stack Compose no ar (ou o script sobe com `--wait`)  
**E** `AZURE_ENABLED=false`  
**Quando** executar o script de smoke Caso vitais  
**Então** o Caso sintético só com vitais alcança `done` dentro do timeout  
**E** o script encerra com código 0  
**E** não há upload de vídeo/áudio/prescrições nesse fluxo.

### Cenário 4 — Smoke no CI

**Dado** o workflow de CI  
**Quando** o job de smoke Compose executar (em `main` e/ou PR — documentar a
matriz escolhida na implementação; se custo/tempo limitar, ao menos em
`main` + opção local)  
**Então** o mesmo contrato do Cenário 3 vale  
**E** `AZURE_ENABLED=false` está efetivo no ambiente do job.

### Cenário 5 — Falha explícita

**Dado** worker indisponível ou Caso que permanece `processing` além do
timeout  
**Quando** o smoke esgotar a espera  
**Então** o script falha com exit ≠ 0  
**E** a mensagem indica `case_id` e último `status` observado.

## Critérios de pronto (DoD desta etapa E8.1)

- [x] Spec SDD aprovada e versionada (esta).
- [x] Script `smoke-caso-vitais` (nome final na implementação) documentado.
- [x] Job/steps: build imagens + publish GHCR só em `main`.
- [x] Job/step de smoke Compose + Caso vitais com `AZURE_ENABLED=false`.
- [x] README/`docs` atualizados no fechamento E8.1 (T8.4).
- [x] Sem E2E UI; sem publish em PR; sem artefatos de E8.2.

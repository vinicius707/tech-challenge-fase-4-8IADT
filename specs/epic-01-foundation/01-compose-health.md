# Fundação — Compose, health e bootstrap

## Objetivo

Definir o ambiente local mínimo do Limen e seu contrato de prontidão. A stack deve
subir de forma reproduzível com Docker Compose, preparar a persistência e informar
se Backend, PostgreSQL, Redis e MinIO estão disponíveis.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 18 de julho de 2026.**

- Contrato `/health` implementado em `backend/app/health.py`, com respostas 200
  e 503, timeouts e supressão de detalhes internos.
- Cinco testes automatizados cobrem prontidão, indisponibilidade individual de
  PostgreSQL, Redis e MinIO e ausência de vazamento de erros.
- `docker-compose.yml` provisiona a infraestrutura e executa o bootstrap
  idempotente do bucket `limen`.
- O entrypoint do backend aplica o baseline Alembic `20260718_0001` antes de
  iniciar a API.
- `scripts/smoke-foundation.sh` valida a stack, o contrato de health, o bucket e
  a revisão do banco.
- A [CI de fechamento](https://github.com/vinicius707/tech-challenge-fase-4-8IADT/actions/runs/29667220157)
  concluiu lint placeholder e pytest com sucesso.

## Escopo

- Backend FastAPI com endpoint público `GET /health`.
- PostgreSQL para o estado de domínio.
- Redis para a fila RQ.
- MinIO para Artefatos, com o bucket `limen`.
- Migrações de banco executadas antes da inicialização do Backend.
- Configuração local documentada por variáveis de ambiente.
- Smoke test local e teste automatizado do contrato de health.

Ficam fora desta etapa autenticação, entidades de domínio, workers RQ, dashboard,
processamento multimodal, Azure e observabilidade além do healthcheck básico.

## ADRs aplicáveis

- [ADR 0002 — Fila Redis + RQ](../../docs/adr/0002-fila-redis-worker.md):
  estabelece o Redis como broker da fila. O worker ainda não faz parte desta
  etapa, mas a fundação deve disponibilizar e verificar o Redis.
- [ADR 0006 — Endurecimento de segurança](../../docs/adr/0006-endurecimento-seguranca.md):
  exige secrets em ambiente. O `.env.example` contém somente nomes e valores
  locais não sensíveis; credenciais reais não são versionadas.
- [ADR 0009 — PostgreSQL + Redis](../../docs/adr/0009-postgres-redis.md):
  reserva o PostgreSQL ao estado de domínio e o Redis à fila RQ. O health não
  deve tratar Redis como banco de domínio.
- [ADR 0011 — Artefatos no MinIO](../../docs/adr/0011-artefatos-minio.md):
  define o object store S3-compatible e o armazenamento no PostgreSQL apenas de
  referências `bucket/key`.
- [ADR 0016 — Outbox leve](../../docs/adr/0016-outbox-leve.md):
  prevê degradação futura quando o Redis estiver indisponível. Nesta etapa,
  porém, `/health` representa a prontidão da stack completa e responde `503`
  enquanto qualquer dependência obrigatória estiver indisponível.
- [ADR 0019 — Observabilidade](../../docs/adr/0019-observabilidade.md):
  requer healthchecks de API e Compose. Azure, métricas, logs correlacionados e
  RQ Dashboard serão incorporados nos épicos em que essas integrações entrarem.
- [ADR 0028 — CI/CD](../../docs/adr/0028-cicd-actions-ghcr.md):
  orienta a evolução da CI. O Épico 1 entrega somente pytest e placeholder de
  lint; build de imagens, smoke com Caso sintético e publicação no GHCR ficam
  para o Épico 8.

## Contrato de health

`GET /health` é um endpoint de prontidão e não exige autenticação. Os checks
executam operações mínimas:

- PostgreSQL: abrir conexão e executar uma consulta simples.
- Redis: abrir conexão e executar `PING`.
- MinIO: acessar o serviço e confirmar que o bucket `limen` existe e está
  acessível com as credenciais configuradas.

Quando todas as dependências estiverem acessíveis, responde `200 OK`:

```json
{
  "status": "ok",
  "checks": {
    "postgres": "ok",
    "redis": "ok",
    "minio": "ok"
  }
}
```

Quando ao menos uma dependência estiver inacessível, responde
`503 Service Unavailable`. Cada dependência conserva seu próprio resultado, e o
resultado da dependência indisponível é `error`:

```json
{
  "status": "error",
  "checks": {
    "postgres": "ok",
    "redis": "error",
    "minio": "ok"
  }
}
```

O endpoint deve ter tempo de resposta limitado por timeouts de conexão, não deve
expor credenciais, URLs internas, stack traces nem mensagens brutas dos provedores.

## Cenários de aceitação

### Cenário 1 — Stack local saudável

**Dado** um ambiente com Docker e Docker Compose e as variáveis obrigatórias
configuradas  
**Quando** o operador executar `docker compose up --build`  
**Então** PostgreSQL, Redis, MinIO e Backend devem iniciar  
**E** os healthchecks do Compose devem ficar saudáveis  
**E** `GET /health` deve responder `200` com `status: "ok"`  
**E** os checks de `postgres`, `redis` e `minio` devem ser `ok`.

### Cenário 2 — PostgreSQL indisponível

**Dado** que o Backend e as demais dependências estejam em execução  
**E** o PostgreSQL esteja inacessível  
**Quando** o operador consultar `GET /health`  
**Então** a resposta deve ter status HTTP `503`  
**E** o status geral deve ser `error`  
**E** o check de `postgres` deve ser `error`  
**E** a resposta não deve revelar credenciais nem detalhes internos da conexão.

### Cenário 3 — Redis indisponível

**Dado** que o Backend e as demais dependências estejam em execução  
**E** o Redis esteja inacessível  
**Quando** o operador consultar `GET /health`  
**Então** a resposta deve ter status HTTP `503`  
**E** o status geral deve ser `error`  
**E** o check de `redis` deve ser `error`  
**E** a resposta deve ser concluída dentro do timeout configurado.

### Cenário 4 — MinIO indisponível

**Dado** que o Backend e as demais dependências estejam em execução  
**E** o MinIO esteja inacessível  
**Quando** o operador consultar `GET /health`  
**Então** a resposta deve ter status HTTP `503`  
**E** o status geral deve ser `error`  
**E** o check de `minio` deve ser `error`  
**E** a resposta deve ser concluída dentro do timeout configurado.

### Cenário 5 — Bootstrap idempotente do bucket

**Dado** que o MinIO esteja saudável  
**Quando** o bootstrap da stack for executado pela primeira vez  
**Então** deve existir exatamente um bucket chamado `limen`  
**Quando** a stack for reiniciada sem remover seus volumes  
**Então** o bootstrap deve terminar com sucesso  
**E** o bucket `limen` e os Artefatos já armazenados devem ser preservados.

### Cenário 6 — Migrações antes do Backend

**Dado** um banco PostgreSQL vazio e saudável  
**Quando** a stack iniciar  
**Então** as migrações Alembic pendentes devem ser aplicadas antes de servir a API  
**E** o Backend só deve ficar saudável após a conclusão das migrações  
**Quando** a stack for reiniciada sem novas migrações  
**Então** a etapa de migração deve terminar sem erro e sem alterar dados existentes.

### Cenário 7 — Configuração por ambiente

**Dado** um clone novo do repositório  
**Quando** o operador consultar `.env.example` e o README  
**Então** deve encontrar todas as variáveis necessárias para executar a stack  
**E** deve conseguir criar sua configuração local sem usar segredos versionados  
**E** o repositório não deve conter credenciais reais.

### Cenário 8 — Verificação automatizada

**Dado** o código do Épico 1  
**Quando** a suíte automatizada for executada  
**Então** deve validar os contratos `200` e `503` de `GET /health` sem depender de
serviços externos reais  
**E** o smoke test local deve validar a stack integrada, o bucket `limen` e as
migrações  
**E** a CI deve executar ao menos os testes Python e reservar uma etapa explícita
para lint  
**E** não deve publicar imagens nem exigir um Caso sintético nesta etapa.

## Definição de pronto — validada

- [x] Todos os cenários desta especificação estão cobertos por teste
  automatizado ou por smoke test documentado, conforme indicado.
- [x] `docker compose up --build` resulta em `GET /health` com HTTP 200.
- [x] O bucket `limen` existe e seu bootstrap é idempotente.
- [x] As migrações estão na revisão mais recente e são idempotentes na
  reinicialização.
- [x] A configuração mínima está documentada sem segredos reais.
- [x] A CI está verde.

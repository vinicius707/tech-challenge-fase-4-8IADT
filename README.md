# Limen

Protótipo acadêmico da FIAP 8IADT — Fase 4 para análise multimodal e detecção
precoce de risco clínico.

> O Limen não é um dispositivo médico e não deve ser usado para decisões
> clínicas reais.

## Stack de fundação

- FastAPI no backend.
- PostgreSQL para estado de domínio.
- Redis para a fila RQ.
- MinIO S3-compatible para Artefatos.
- Alembic para versionamento do schema.
- Docker Compose para execução local.

As decisões estão registradas em [`docs/adr/`](docs/adr/), especialmente as ADRs
[0009](docs/adr/0009-postgres-redis.md),
[0011](docs/adr/0011-artefatos-minio.md) e
[0019](docs/adr/0019-observabilidade.md).

## Executar localmente

Pré-requisitos:

- Docker com Docker Compose v2.
- Portas 5432, 6379, 8000, 9000 e 9001 disponíveis, ou portas alternativas
  configuradas no `.env`.

Crie a configuração local e suba a stack:

```bash
cp .env.example .env
docker compose up --build --wait
```

O Compose aguarda PostgreSQL, Redis e MinIO, cria o bucket `limen`, aplica
`alembic upgrade head` e só então inicia o backend.

Verifique a prontidão:

```bash
curl http://localhost:8000/health
```

Resposta esperada:

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

Endpoints locais:

- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>
- Console MinIO: <http://localhost:9001>

Para encerrar sem apagar dados:

```bash
docker compose down
```

Para recriar o ambiente do zero, remova também os volumes. Esse comando apaga
o banco e todos os Artefatos locais:

```bash
docker compose down -v
```

## Configuração e secrets

O arquivo `.env.example` contém somente valores locais demonstrativos. O `.env`
é ignorado pelo Git e não deve conter credenciais reais versionadas. Em ambientes
compartilhados, substitua todas as senhas e use o mecanismo de secrets da
plataforma.

As variáveis disponíveis controlam credenciais, nomes de recursos, portas e o
timeout do healthcheck. `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`
também compõem automaticamente a URL usada pelo backend.

A futura chave `PII_ENCRYPTION_KEY`, introduzida com o Rótulo Sensível no Épico
2, deverá existir somente no ambiente. Sua rotação será manual: pausar escritas,
manter a chave anterior durante a recriptografia dos dados, validar a leitura com
a nova chave e só então remover a anterior. Substituir a chave sem recriptografar
torna os dados existentes ilegíveis.

## Testes do backend

Com Python 3.12 e `uv` instalados:

```bash
cd backend
uv sync
uv run pytest
```
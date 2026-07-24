FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Extras opcionais (Épico 11 / ADR 0030): vazios na API/worker padrão.
# worker-video real: docker compose -f docker-compose.yml -f docker-compose.video-real.yml
ARG LIMEN_UV_EXTRAS=""

COPY pyproject.toml uv.lock ./
RUN if [ -z "$LIMEN_UV_EXTRAS" ]; then \
      uv sync --frozen --no-dev; \
    else \
      extras=""; \
      for e in $LIMEN_UV_EXTRAS; do extras="$extras --extra $e"; done; \
      uv sync --frozen --no-dev $extras; \
    fi

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/limen-entrypoint
RUN chmod +x /usr/local/bin/limen-entrypoint

EXPOSE 8000

ENTRYPOINT ["limen-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

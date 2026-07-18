# Fila de processamento: Redis + RQ

O ciclo de vida completo do Caso (`pending`/`processing`/`done`/`failed`/`cancelled`, retries e dead-letter) usa **Redis Queue (RQ)** com Redis e um processo worker no Docker Compose. Analogia ao dia a dia com SQS + Lambda: enqueue ≈ send message, worker ≈ consumer, failed registry ≈ DLQ após max retries. Motivo: robustez operacional, aprendizado transferível de filas, sem o overhead de Celery. Alternativas rejeitadas: ARQ (menos alinhado ao padrão clássico); Celery+RabbitMQ (excessivo); jobs só em SQLite.

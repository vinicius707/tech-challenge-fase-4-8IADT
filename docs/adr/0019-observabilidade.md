# Observabilidade: logs, healthchecks, métricas e RQ Dashboard

A stack inclui logs estruturados com `caso_id`/`job_id`, healthchecks Compose/API (Postgres, Redis, MinIO, Azure), endpoint de métricas simples (fila, latência por modalidade, estado do circuit breaker) e RQ Dashboard no Compose como ferramenta de operador para inspecionar filas/DLQ. Alternativa rejeitada: Prometheus+Grafana nesta fase (overhead de ops sem ganho proporcional ao PDF).

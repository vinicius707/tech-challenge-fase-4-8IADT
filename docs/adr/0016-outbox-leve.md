# Outbox leve: Postgres como fonte da verdade, RQ como dispatcher

Transições de processamento do Caso (incl. reprocessamento seletivo) são gravadas primeiro numa tabela de outbox/jobs no PostgreSQL. O Redis/RQ despacha o trabalho; se Redis estiver indisponível, os jobs permanecem pendentes no outbox e um reconciler os enfileira quando a fila voltar. Postgres down → API 503; MinIO down → rejeita novos uploads de Artefato. Alternativas rejeitadas: fail-fast total sem degradação; outbox/event bus completo fora do escopo.

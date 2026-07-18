# Artefatos multimodais no MinIO

Vídeos, áudios, CSVs e frames anotados ficam no MinIO (S3-compatible) no Docker Compose; Postgres guarda metadados e referências (bucket/key). Motivo: padrão próximo a S3/Lambda do dia a dia, sem depender de Azure Blob fora do F0 de Cognitive Services. Alternativas rejeitadas: só disco local (menos alinhado a produção); Azure Blob nesta fase (outra conta/cota).

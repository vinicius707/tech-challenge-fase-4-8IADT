# Painel de Falhas de Processamento (DLQ)

Falhas após max retries no RQ são expostas na API/UI como Falhas de Processamento: listar, inspecionar exceção, redrive (reenqueue) e descartar — paralelo explícito a DLQ/redrive de SQS. Não se confundem com Alertas clínicos. Alternativa rejeitada: apenas status `failed` no Caso sem painel operacional.

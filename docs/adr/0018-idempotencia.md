# Idempotência: create, worker e Alertas

Três camadas de idempotência: (1) criação de Caso usa Idempotency-Key + hash dos Artefatos — mesmo Paciente com mesmos hashes devolve o Caso existente; (2) o worker verifica se a modalidade já está `done` antes de processar (redrive seguro); (3) Alertas são deduplicados por `(caso_id, nível, versão)`, impedindo spam no feed SSE após reprocessamento. Paralelo intencional com consumo at-least-once de SQS. Alternativa rejeitada: confiar apenas no comportamento do cliente.

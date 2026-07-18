# Falha parcial e reprocessamento seletivo de modalidades

Um Caso pode concluir (`done`) com um subconjunto de modalidades bem-sucedidas; modalidades com falha ficam `failed` e entram na Justificativa como indisponíveis. O reprocessamento enfileira job RQ apenas para modalidades `failed`, reutiliza Artefatos no MinIO e refundição o Risco ao terminar. Alternativas rejeitadas: falha total do Caso por uma modalidade; reprocessar sempre todas as modalidades (custo/cota Azure).

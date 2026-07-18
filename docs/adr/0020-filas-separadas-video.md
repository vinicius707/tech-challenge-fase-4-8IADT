# Filas RQ separadas por carga

Processamento usa filas distintas: `video` (worker dedicado, CPU-heavy) e `default` (áudio, vitais, prescrições, fusão/refundição). Evita que um vídeo longo monopolize o reprocessamento de modalidades leves. No Compose, dois containers worker com conjuntos de filas diferentes. Alternativa rejeitada: um único worker serial; N workers na mesma fila sem isolamento de carga.

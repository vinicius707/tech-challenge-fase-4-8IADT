# Retries classificados + circuit breaker Azure

Erros de processamento são classificados: transitórios (429, timeout) usam retry com backoff exponencial na fila RQ; permanentes (arquivo inválido, auth) vão direto para modalidade `failed`/DLQ; quota/indisponibilidade Azure dispara fallback local na mesma tentativa. Além disso, um circuit breaker abre após N falhas Azure consecutivas e força provedor local por T minutos, protegendo a cota F0. Alternativa rejeitada: retry cego para qualquer erro.

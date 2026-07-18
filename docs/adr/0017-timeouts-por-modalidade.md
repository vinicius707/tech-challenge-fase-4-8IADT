# Timeouts por modalidade via RQ

Cada modalidade tem timeout configurável (ex.: áudio 90s, vitais 30s, vídeo 180s). Estouro marca a modalidade como `failed` e as demais seguem (falha parcial). O cancelamento é feito pelo timeout do job RQ, sem cancelamento cooperativo nem retomada de progresso parcial no loop de frames. Motivo: previsibilidade e menor superfície de bugs no prazo acadêmico. Alternativa rejeitada: cancelamento cooperativo com estado parcial (caro de modelar/testar para cenário raro na demo).

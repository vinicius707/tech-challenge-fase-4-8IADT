# SSE de Alertas via fetch + ReadableStream

O feed de Alertas no frontend não usa `EventSource` nativo. Consome SSE com `fetch` e header `Authorization: Bearer`, lendo o corpo como stream. Motivo: JWT não vai na query string (higiene/privacidade); reutiliza o mesmo cliente autenticado da API. Alternativas rejeitadas: token na query; cookie httpOnly+CSRF nesta fase.

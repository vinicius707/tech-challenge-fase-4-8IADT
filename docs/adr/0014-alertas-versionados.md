# Alertas versionados após reprocessamento

Cada Alerta clínico pertence a um Caso e é versionado de forma append-only. Quando o reprocessamento seletivo altera o Risco (cruzamento de limiar ou mudança de nível), cria-se uma nova versão do mesmo Alerta; o feed SSE emite atualização. Versões anteriores permanecem para auditoria e Justificativa. Alternativas rejeitadas: um Alerta novo desconectado a cada mudança; update in-place sem histórico.

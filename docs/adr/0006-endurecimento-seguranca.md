# Endurecimento de segurança no protótipo

Além de secrets em ambiente, a aplicação inclui: CORS restrito, rate limit no login, headers de segurança no frontend/nginx, senha de Operador com bcrypt, JWT com expiração curta e Registro de Auditoria para desmascarar Rótulo Sensível e ações de DLQ. Fora do escopo desta fase: rotação automática de chave PII com re-encrypt, HTTPS local obrigatório e scanning de deps como gate de CI (podem constar como próximos passos no relatório).

**Emenda (Épico 2):** refresh tokens com rotação e logout com blacklist passam a fazer parte do protótipo, conforme o plano incremental e a spec `specs/epic-02-identity/01-auth-login.md`. A exclusão anterior de refresh tokens fica supersedida.

# Autenticação JWT com papéis medico e admin

Acesso ao frontend/API exige login JWT de Operador. Papel `medico` cobre
Pacientes, Casos, Alertas e visualização mascarada/desmascarada do Rótulo
Sensível; papel `admin` inclui o painel de Falhas de Processamento (DLQ/redrive).
Credenciais seed/`.env` para demo.

**Status (Épico 2):** login, refresh rotativo, logout com blacklist, rate limit
e seed implementados (`specs/epic-02-identity/01-auth-login.md`).

Alternativas rejeitadas: app totalmente aberta (enfraquece a narrativa de
privacidade); RBAC completo com muitos papéis (fora do escopo).

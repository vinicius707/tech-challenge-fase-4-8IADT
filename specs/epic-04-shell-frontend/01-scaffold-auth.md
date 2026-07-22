# Shell Frontend — Scaffold Next e autenticação na UI

## Objetivo

Definir o bootstrap do frontend Limen: aplicação Next.js (App Router) com
Tailwind e shadcn/ui, proxy `/api` para o FastAPI, sessão do Operador em
Zustand (access + refresh), rota pública `/login` e shell autenticado com
landmarks acessíveis e layout responsivo.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Parcial — T4.0–T4.2:** specs + scaffold + proxy + sessão Zustand + `/login`
+ guard + logout. Shell landmarks: **T4.3**.

## Escopo

- App em `frontend/` (ou diretório equivalente documentado) com Next.js App
  Router, TypeScript, Tailwind CSS e primitives shadcn/ui.
- Rewrite/proxy de `/api/*` para o backend FastAPI (sem Route Handlers BFF e
  sem motores de IA em Node).
- Sessão em Zustand: access token, refresh token, papel (`medico` | `admin`),
  username; renovação transparente do access via refresh quando expirar.
- Rota pública `/login` (formulário username/senha → `POST /api/auth/login`).
- Guard de rotas: não autenticado → `/login`; autenticado em `/login` → `/`
  (ou dashboard mínimo).
- Shell pós-login com landmarks (`header`/`nav`/`main`), navegação mínima
  (Pacientes; placeholder ou link desabilitado para Alertas/Admin se fora
  deste épico) e layout responsivo (mobile + desktop).
- Logout: chama `POST /api/auth/logout` e limpa a sessão no cliente.
- Testes automatizados do fluxo de login (sucesso, credencial inválida,
  redirecionamento).
- Integração mínima no Compose/`README` para subir o frontend em local
  (porta documentada).

Ficam fora desta etapa: listagem de Pacientes/Casos (spec `02`); baseline
Lighthouse (spec `03`); dark mode; AA fino / auditoria a11y completa; SSE de
Alertas; `/admin/falhas`; Justificativa rica; Recharts; i18n; OAuth/OIDC/MFA;
cookies httpOnly como estratégia principal de sessão nesta fase.

## ADRs aplicáveis

- [ADR 0023 — Next.js App Router](../../docs/adr/0023-frontend-nextjs.md):
  front-only; proxy `/api` → FastAPI.
- [ADR 0024 — Tailwind + shadcn](../../docs/adr/0024-ui-tailwind-shadcn.md):
  primitives de UI.
- [ADR 0025 — Query + Zustand](../../docs/adr/0025-estado-query-zustand.md):
  sessão no Zustand; server state no TanStack Query (Query entra de fato na
  spec `02`).
- [ADR 0026 — Rotas](../../docs/adr/0026-rotas-frontend.md): neste épico só
  `/login` e o shell; demais rotas nas specs seguintes / épicos seguintes.
- [ADR 0004](../../docs/adr/0004-auth-jwt-papeis.md) /
  [ADR 0021](../../docs/adr/0021-auth-api-papeis.md): contratos de auth da API.

## Contratos de UI (mínimos)

### `/login`

- Campos: username, senha; CTA de entrar.
- Sucesso: persiste tokens na sessão Zustand e redireciona para área autenticada.
- Falha `401` (ou equivalente da API): mensagem de erro sem vazar detalhes de
  implementação; não grava sessão.
- Sem Bearer válido: rota acessível.

### Shell autenticado

- Landmarks: navegação principal e conteúdo principal identificáveis.
- Exibe username (e opcionalmente papel) do Operador.
- Ação de logout visível.
- Em viewport estreita: navegação usável (menu colapsável ou equivalente), sem
  exigir scroll horizontal do chrome.

### Proxy `/api`

- Chamadas do browser usam caminhos relativos `/api/...`.
- O rewrite encaminha para o backend (URL configurável por ambiente, ex.
  `http://backend:8000` no Compose).

## Cenários de aceitação

### Cenário 1 — Login válido

**Dado** Operador seed existente no backend  
**Quando** submeter credenciais corretas em `/login`  
**Então** a sessão deve conter access (e refresh)  
**E** o usuário deve ser redirecionado para a área autenticada.

### Cenário 2 — Login inválido

**Dado** credenciais incorretas  
**Quando** submeter o formulário  
**Então** deve exibir erro  
**E** não deve haver sessão autenticada.

### Cenário 3 — Guard

**Dado** ausência de sessão  
**Quando** acessar uma rota autenticada do shell  
**Então** deve redirecionar para `/login`.

### Cenário 4 — Logout

**Dado** Operador autenticado  
**Quando** acionar logout  
**Então** a sessão local deve ser limpa  
**E** uma nova visita a rota autenticada exige login.

### Cenário 5 — Proxy

**Dado** frontend e backend no ar  
**Quando** o login chamar `/api/auth/login`  
**Então** a requisição deve ser atendida pelo FastAPI via rewrite (sem CORS
obrigatório browser→backend direto nesta configuração).

## Critérios de pronto (DoD desta spec / T4.1–T4.3)

- [x] Scaffold Next + Tailwind + shadcn commitado e documentado. *(T4.1)*
- [x] Proxy `/api` configurado; Compose/README atualizados se necessário. *(T4.1)*
- [x] Zustand de sessão + `/login` + guard + logout. *(T4.2)*
- [ ] Shell com landmarks responsivo.
- [x] Cenários 1–5 cobertos por testes automatizados (e/ou e2e leve acordado). *(T4.2: 1–4 + rewrite; proxy em T4.1)*

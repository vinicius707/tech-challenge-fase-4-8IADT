# Shell Frontend — Pacientes, Novo Caso vitais e detalhe

## Objetivo

Definir as telas mínimas do fluxo clínico visual do Limen: listar/detalhar
Pacientes, criar Caso com upload de vitais vinculado ao Paciente, e acompanhar
o detalhe do Caso até `done` com Risco e Alerta v1 em modo somente leitura —
usando TanStack Query (polling/skeletons) sobre a API do Épico 3.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 21 de julho de 2026** (T4.4–T4.6): Pacientes, Novo Caso vitais e
detalhe de Caso com polling/skeletons + Risco/Alerta read-only.

## Escopo

- Rotas (ADR 0026, subconjunto deste épico):
  - `/pacientes` — listagem
  - `/pacientes/[id]` — detalhe mínimo do Paciente (código `PAC-NNN`, rótulo
    mascarado; sem reveal obrigatório nesta etapa)
  - `/pacientes/[id]/novo-caso` — upload CSV de vitais + `Idempotency-Key`
  - `/casos/[id]` — detalhe: status, modalidades, `risk_score` / `risk_level`,
    Alertas se existirem
- Server state via TanStack Query; sessão permanece no Zustand (spec `01`).
- Enquanto o Caso estiver `pending`/`processing`: polling periódico do GET e
  skeletons/placeholders de carregamento.
- Risco e Alerta: exibição read-only (sem editar, sem SSE, sem Justificativa
  rica).
- Papéis: `medico` e `admin` usam as mesmas telas neste épico (sem UI de DLQ).

Ficam fora desta etapa: tendência de risco do Paciente com gráficos (Recharts /
Épico 7); reveal de Rótulo Sensível na UI (pode ficar como link/ação futura);
SSE `/alertas`; `/admin/falhas`; dark mode; AA fino; Justificativa por
template completo; modalidades `video`/`audio`/`prescriptions`; edição de
Caso; paginação avançada além do mínimo útil.

## ADRs aplicáveis

- [ADR 0026 — Rotas](../../docs/adr/0026-rotas-frontend.md): mapa canônico;
  neste épico só o subconjunto listado.
- [ADR 0025 — Query + Zustand](../../docs/adr/0025-estado-query-zustand.md):
  Casos/Pacientes no Query; polling de `processing`.
- [ADR 0023](../../docs/adr/0023-frontend-nextjs.md) /
  [ADR 0024](../../docs/adr/0024-ui-tailwind-shadcn.md): stack UI.
- Contratos de API: specs do Épico 3
  ([`03-caso-vitais-risco`](../epic-03-caso-fila/03-caso-vitais-risco.md)) e
  Épico 2 ([`02-paciente-privacidade`](../epic-02-identity/02-paciente-privacidade.md)).

## Contratos de UI (mínimos)

### `/pacientes`

- Lista Pacientes (código + máscara de rótulo se houver).
- CTA para abrir detalhe; CTA para criar Paciente mínimo (se a API já expõe
  `POST /patients` sem campos obrigatórios além do autenticado).

### `/pacientes/[id]`

- Exibe código e dados mascarados.
- CTA **Novo Caso** → `/pacientes/[id]/novo-caso`.
- Lista curta de Casos do Paciente **se** a API expuser listagem; caso
  contrário, apenas o CTA de novo Caso e navegação manual por id (documentar a
  lacuna; não inventar endpoint backend neste épico).

### `/pacientes/[id]/novo-caso`

- Upload de arquivo CSV de vitais.
- Envio com `Idempotency-Key` (gerada no cliente por tentativa de submit).
- Sucesso: navega para `/casos/{id}` do Caso criado (ou retornado por replay
  idempotente).
- Erros de API (`404` Paciente, `503` storage, `401`) com feedback visível.

### `/casos/[id]`

- Status do Caso e da modalidade `vitals`.
- Após `done`: `risk_score`, `risk_level`; lista de Alertas (`level`, `version`)
  se houver; ausência de Alerta quando `BAIXO`.
- Em `pending`/`processing`: skeleton + polling até estado terminal (`done` /
  `failed`) ou timeout de UX documentado (sem DLQ UI).

## Cenários de aceitação

### Cenário 1 — Listar Pacientes

**Dado** Operador autenticado e ≥1 Paciente na API  
**Quando** abrir `/pacientes`  
**Então** deve listar os códigos (e máscara de rótulo quando aplicável).

### Cenário 2 — Novo Caso vitais

**Dado** Paciente existente e fixture `vitals_medium`  
**Quando** enviar o CSV em `/pacientes/[id]/novo-caso`  
**Então** deve obter um `case_id`  
**E** ser levado a `/casos/{id}`.

### Cenário 3 — Polling até Risco

**Dado** Caso em processamento  
**Quando** permanecer em `/casos/[id]`  
**Então** a UI deve atualizar até `done`  
**E** exibir `risk_level` (ex.: `MEDIO`) e Alerta v1 quando aplicável.

### Cenário 4 — BAIXO sem Alerta

**Dado** Caso processado com fixture `vitals_normal`  
**Quando** abrir o detalhe  
**Então** `risk_level` deve ser `BAIXO`  
**E** não deve haver Alerta listado.

### Cenário 5 — Auth

**Dado** ausência de sessão  
**Quando** acessar qualquer rota desta spec  
**Então** deve redirecionar para `/login`.

## Critérios de pronto (DoD desta spec / T4.4–T4.6)

- [x] Rotas de Pacientes, Novo Caso e detalhe de Caso implementadas. *(T4.4–T4.6)*
- [x] Query + polling/skeletons no detalhe enquanto não terminal. *(T4.6; intervalo 2s, timeout de UX 120s)*
- [x] Risco/Alerta somente leitura conforme API do Épico 3. *(T4.6)*
- [x] Cenários 1–5 cobertos por testes automatizados (e/ou e2e leve). *(helpers + create + parse detalhe/polling; auth via AuthGate)*
- [x] Fluxo visual Paciente → Caso → Risco demonstrável em local.

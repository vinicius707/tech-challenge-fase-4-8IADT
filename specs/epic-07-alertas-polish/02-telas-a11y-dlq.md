# Alertas + polish — Telas estrela, a11y AA e DLQ UI (E7.2)

## Objetivo

Polir as **telas estrela** da demo (Caso ~70% do esforço visual + fecho
Paciente/Alertas): tema dark/light, WCAG 2.2 AA, toasts e região de Alertas
navegável, upload acessível, reveal de Rótulo Sensível com SR, Recharts lazy
e UI admin de Falhas de Processamento (API já existe no Épico 5).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 22 de julho de 2026** (T7.6–T7.11: dark/light AA, toast polite,
região Alertas, uploads a11y, reveal+SR, Recharts lazy, UI admin DLQ e
fechamento docs).

Etapa posterior do Épico 7 (spec própria):

- E7.3 — Gate Lighthouse por regressão vs baseline (concluída)

## Escopo

- Tema **dark / light** (toggle persistente; contraste AA).
- Auditoria e ajustes **WCAG 2.2 AA** nas rotas estrela:
  `/casos/[id]`, `/pacientes/[id]`, listagem de Alertas (ou região no shell),
  `/login` se regressões.
- Toast `aria-live="polite"` para eventos de Alerta (SSE da E7.1); região de
  Alertas **navegável por teclado** (landmarks / headings / lista focável).
- Upload de modalidades (vitais / vídeo / áudio / prescriptions) com rótulos,
  erros associados (`aria-describedby`), foco e teclado.
- Reveal de Rótulo Sensível: confirmação, audit já existente, anúncio SR
  (`aria-live`) ao mascarar/desmascarar.
- **Recharts** via `next/dynamic` só em `/pacientes/[id]` e `/casos/[id]`
  (ADR 0027): tendência de Risco e/ou séries vitais mínimas.
- UI **admin** `/admin/falhas` (ou rota alinhada a ADR 0026): listar,
  detalhe, redrive e discard contra `GET/POST /admin/failures*`; `medico`
  recebe `403` na API e não vê a rota (ou vê bloqueio explícito).
- Justificativa da E7.1 integrada ao layout estrela do Caso (hierarquia
  visual, sem mudar o contrato backend salvo bugs).

Ficam fora desta etapa: gate Lighthouse no CI (E7.3); GHCR / smoke Compose
(Épico 8); i18n; OAuth/OIDC/MFA; redesign completo fora das rotas estrela;
Prometheus.

## ADRs aplicáveis

- [ADR 0023 — Frontend Next.js](../../docs/adr/0023-frontend-nextjs.md)
- [ADR 0024 — Tailwind + shadcn](../../docs/adr/0024-ui-tailwind-shadcn.md)
- [ADR 0025 — Estado Query/Zustand](../../docs/adr/0025-estado-query-zustand.md)
- [ADR 0026 — Rotas frontend](../../docs/adr/0026-rotas-frontend.md)
- [ADR 0027 — Recharts lazy](../../docs/adr/0027-graficos-recharts-lazy.md)
- [ADR 0003 — Painel DLQ / redrive](../../docs/adr/0003-painel-dlq-redrive.md)
- [ADR 0001 — Privacidade Paciente](../../docs/adr/0001-privacidade-paciente.md)
- [ADR 0022 — SSE fetch](../../docs/adr/0022-sse-fetch-stream.md) (consumo UI)

## Contratos / rotas (mínimos)

| Superfície | Nota |
| ---------- | ---- |
| `/casos/[id]` | Justificativa, gráficos lazy, uploads a11y, status modalidades |
| `/pacientes/[id]` | Rótulo + reveal SR; tendência; atalhos para Casos/Alertas |
| Região / página Alertas | Lista navegável + toasts `polite` |
| `/admin/falhas` | Só `admin`; redrive/discard |

API DLQ já coberta no Épico 5 — esta etapa é UI + a11y.

## Cenários de aceitação

### Cenário 1 — Tema

**Dado** Operador na UI  
**Quando** alternar dark/light  
**Então** o tema persiste no reload  
**E** textos/controles críticos mantêm contraste AA nas telas estrela.

### Cenário 2 — Toast de Alerta

**Dado** SSE conectado (E7.1)  
**Quando** chegar `alert.created` / `alert.updated`  
**Então** um toast `aria-live="polite"` anuncia o evento  
**E** a região de Alertas permanece navegável por teclado.

### Cenário 3 — Upload acessível

**Dado** formulário de anexo de modalidade no Caso  
**Quando** houver erro de validação ou sucesso  
**Então** a mensagem está associada ao controle  
**E** o fluxo é operável só com teclado.

### Cenário 4 — Reveal + SR

**Dado** Paciente com Rótulo Sensível  
**Quando** desmascarar (com audit)  
**Então** leitores de tela recebem anúncio da mudança  
**E** remascarar também é anunciado.

### Cenário 5 — Recharts lazy

**Dado** build de produção  
**Quando** carregar `/login` ou listagem sem gráficos  
**Então** Recharts não entra no bundle inicial dessas rotas  
**E** em `/casos/[id]` / `/pacientes/[id]` os gráficos carregam sob demanda.

### Cenário 6 — DLQ UI admin

**Dado** `admin` autenticado com Falha de Processamento aberta  
**Quando** abrir `/admin/falhas`, inspecionar e redrive/discard  
**Então** a UI reflete a API  
**E** `medico` não opera o painel (403 / rota ausente).

## Critérios de pronto (DoD desta etapa E7.2)

- [x] Dark/light + AA nas telas estrela.
- [x] Toast polite + região Alertas navegável.
- [x] Uploads a11y; reveal rótulo + SR.
- [x] Recharts lazy (ADR 0027).
- [x] UI admin DLQ funcional.
- [x] Sem gate Lighthouse CI (E7.3); sem Épico 8.
- [x] Guia de uso / docs frontend atualizados no fechamento da etapa.

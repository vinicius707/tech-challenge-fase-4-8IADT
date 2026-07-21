# Shell Frontend — Baseline Lighthouse

## Objetivo

Registrar uma baseline versionada de performance/a11y/SEO do shell Limen via
Lighthouse, sem gate de CI neste épico — apenas artefato em
`docs/perf/baseline/` para comparação futura (Épico 7 / Épico 8).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Spec aprovada (T4.0).** Implementação: **T4.7**.

## Escopo

- Executar Lighthouse (Chrome) contra o frontend local (ou URL documentada) nas
  rotas mínimas do Épico 4: `/login` e pelo menos uma rota autenticada
  representativa (ex.: `/pacientes` ou `/casos/[id]` após seed/demo).
- Persistência dos relatórios (JSON e/ou HTML) e um README curto em
  `docs/perf/baseline/` descrevendo: data, commit/SHA, ambiente (desktop/mobile),
  como regenerar.
- Sem falhar CI se scores forem baixos; sem budgets enforçados nesta etapa.

Ficam fora desta etapa: gate de Lighthouse no CI; budgets oficiais; dark mode;
auditoria AA completa; otimização agressiva de bundle; Recharts; SSE.

## ADRs aplicáveis

- [ADR 0023 — Next.js](../../docs/adr/0023-frontend-nextjs.md): alvo da medição.
- Plano incremental: polish a11y/Lighthouse no Épico 7; CI/CD no Épico 8.

## Cenários de aceitação

### Cenário 1 — Baseline versionada

**Dado** o frontend do Épico 4 no ar  
**Quando** gerar o relatório Lighthouse das rotas mínimas  
**Então** os artefatos devem existir em `docs/perf/baseline/`  
**E** o README deve explicar como reproduzir.

### Cenário 2 — Sem gate

**Dado** a pipeline CI atual  
**Quando** um score Lighthouse for baixo  
**Então** o CI **não** deve falhar por causa desta baseline (nenhum step de
gate adicionado neste épico).

## Critérios de pronto (DoD desta spec / T4.7)

- [ ] `docs/perf/baseline/` com relatórios + README de regeneração.
- [ ] Referência cruzada no README principal ou `docs/README.md`.
- [ ] Nenhum gate de Lighthouse adicionado ao CI nesta etapa.

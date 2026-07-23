# Alertas + polish — Gate Lighthouse por regressão (E7.3)

## Objetivo

Transformar o baseline Lighthouse do Épico 4 em **gate de CI por regressão**:
limites absolutos (Perf ≥90, A11y ≥95, Best Practices ≥90) **e** não piorar
além de uma tolerância documentada vs `docs/perf/baseline/`.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** — executar após DoD de E7.1 e E7.2 (T7.12–T7.14 desta etapa E7.3).

## Escopo

- Job (ou step) de Lighthouse no CI do frontend medindo ao menos as rotas do
  baseline (`/login`, `/pacientes`) e, se estável no CI, `/casos/[id]` com
  sessão sintética documentada.
- **Limites absolutos** (desktop, formFactor alinhado ao baseline):
  - Performance ≥ **90**
  - Accessibility ≥ **95**
  - Best Practices ≥ **90**
  - SEO: informar no relatório; gate opcional (baseline já ~100)
- **Gate por regressão**: falhar se score &lt; baseline − tolerância (ex.:
  −2 pontos) **ou** &lt; limite absoluto — o que for mais restritivo.
- Artefatos de relatório no CI (HTML/JSON) para inspeção em PRs.
- Script local reutilizando `scripts/lighthouse-baseline.mjs` (ou sucessor)
  com modo `check` vs `docs/perf/baseline/summary.json`.
- Atualizar `docs/perf/baseline/` só em commit explícito de “novo baseline”
  (não silenciosamente a cada PR).

Ficam fora desta etapa: publish GHCR; smoke Compose end-to-end de Caso
vitais; seed/notebooks/relatório final (Épico 8); mobile formFactor
obrigatório; orçamento de bundle Webpack aparte.

## ADRs aplicáveis

- Baseline Épico 4: [`docs/perf/baseline/`](../../docs/perf/baseline/)
- [ADR 0023 — Frontend Next.js](../../docs/adr/0023-frontend-nextjs.md)
- [ADR 0028 — CI/CD Actions/GHCR](../../docs/adr/0028-cicd-actions-ghcr.md)
  (CI já existe; **publish GHCR** continua no Épico 8)

## Cenários de aceitação

### Cenário 1 — Gate absoluto

**Dado** build de produção do frontend no CI  
**Quando** rodar Lighthouse nas rotas gate  
**Então** Perf ≥90, A11y ≥95, BP ≥90  
**E** o job falha se algum limite absoluto for violado.

### Cenário 2 — Gate por regressão

**Dado** `docs/perf/baseline/summary.json` versionado  
**Quando** um score cair mais que a tolerância vs baseline  
**Então** o CI falha mesmo que ainda esteja acima do piso absoluto  
**E** a mensagem aponta rota + categoria + delta.

### Cenário 3 — Baseline intocado por acaso

**Dado** PR que não atualiza baseline  
**Quando** o gate passa  
**Então** `docs/perf/baseline/` permanece inalterado no diff  
**E** relatórios do run ficam só como artefato de CI.

### Cenário 4 — Script local

**Dado** frontend em `npm start` local  
**Quando** rodar o script em modo check  
**Então** o resultado espelha a regra do CI (pass/fail documentado).

## Critérios de pronto (DoD desta etapa E7.3)

- [ ] Gate Lighthouse no CI (absoluto + regressão).
- [ ] Tolerância e rotas documentadas em `docs/perf/` + README.
- [ ] Fechamento docs do Épico 7 (índice specs, plano, guia se afetado).
- [ ] Sem GHCR publish / smoke Compose de entrega (Épico 8).

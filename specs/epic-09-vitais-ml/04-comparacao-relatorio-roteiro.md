# Épico 9 — Comparação, relatório e roteiro (E9.4)

## Objetivo

Fechar a narrativa acadêmica/portfólio do Épico 9: comparar **limiares vs
Isolation Forest vs autoencoder**, atualizar relatório e roteiro de vídeo, e
deixar o caminho de demo com `hybrid` documentado — **sem** novas features de
UI além do necessário para contar a história.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** — spec apenas (SDD). Depende de E9.1–E9.3 entregues (ou stubs
mínimos acordados). Esta etapa **não** implementa o motor; consolida evidência.

## Escopo

- Notebook ou seção de notebook com comparação quantitativa em holdout
  (precision/recall e/ou AUROC / agreement com labels das fixtures e amostra
  processada — métricas exatas na implementação, desde que reportáveis).
- Emenda a [`docs/relatorio-fase4.md`](../../docs/relatorio-fase4.md):
  seção ML vitais (ETL, IF, AE, limites clínicos, ADR 0029).
- Emenda a [`docs/demo/roteiro-video.md`](../../docs/demo/roteiro-video.md):
  ~90% app (fixtures/seed, idealmente `hybrid`) + ~10% notebook (loss/epochs +
  catálogo).
- Atualizar índices: [`docs/README.md`](../../docs/README.md),
  [`README.md`](../../README.md), [`notebooks/README.md`](../../notebooks/README.md)
  conforme o que a implementação realmente entregou.
- Checklist de gravação alinhado ao “pronto para gravar” cheio acordado no
  discovery (comparação + relatório + roteiro).

Ficam fora desta etapa: reabrir escopo de vídeo/áudio ML; deploy cloud;
tornar Azure obrigatório; E2E Playwright.

## ADRs aplicáveis

- [ADR 0029 — Vitais ML híbrido](../../docs/adr/0029-vitais-ml-hibrido.md)
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md)
- [ADR 0028 — CI/CD](../../docs/adr/0028-cicd-actions-ghcr.md) (CI segue magro)

## Cenários de aceitação

### Cenário 1 — Comparação reproduzível

**Dado** limiares, IF e AE disponíveis conforme E9.2/E9.3  
**Quando** abrir o notebook/seção de comparação  
**Então** há tabela ou figuras contrastando os três enfoques  
**E** fica explícito o que roda na API vs só evidência.

### Cenário 2 — Relatório

**Dado** `docs/relatorio-fase4.md`  
**Quando** ler a seção nova de ML vitais  
**Então** cita ADR 0029, datasets do ETL, flag de backend e exclusão do AE do
runtime.

### Cenário 3 — Roteiro

**Dado** `docs/demo/roteiro-video.md`  
**Quando** um apresentador seguir o roteiro  
**Então** a demo prioriza a app multimodal e reserva tempo curto ao notebook  
**E** não instrui download ao vivo de dataset durante a gravação.

## Critérios de pronto (DoD E9.4)

- [ ] Spec SDD aprovada (esta).
- [ ] Comparação limiares/IF/AE versionada (notebook).
- [ ] Relatório e roteiro emendados.
- [ ] Índices README atualizados.
- [ ] Baseline (`00`) ainda descreve o “antes”; pós-E9 documenta o “depois”.

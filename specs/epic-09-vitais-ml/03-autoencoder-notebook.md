# Épico 9 — Autoencoder PyTorch (notebook + export) (E9.3)

## Objetivo

Entregar evidência de treino com **epochs** via autoencoder PyTorch em
notebook, com export opcional de pesos, **sem** carregar AE no worker.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Pendente** — spec apenas (SDD). Depende de E9.1 (dados processados); pode
rodar em paralelo documental com E9.2, mas a comparação completa fecha em E9.4.

## Escopo

- Novo notebook sob `notebooks/` (ex.: `train_vitals_autoencoder.ipynb`) que:
  - carrega features de `data/processed/vitals/` (ou amostra documentada);
  - treina AE em PyTorch com epochs, loss e early stopping;
  - plota curvas; exporta pesos opcionalmente (ex.: `models/vitals/ae_export.pt`
    — gitignored se grande, ou amostra mínima documentada).
- Extra de deps **fora** do backend: ex. `notebooks/requirements-ml.txt` ou
  grupo documentado no README dos notebooks (`torch`, etc.).
- `notebooks/README.md` atualizado: como criar o env ML, que o CI **não** roda
  este notebook.
- Explicitamente **fora**: `LIMEN_VITALS_BACKEND=autoencoder`; import de
  `torch` em `backend/app/`.

Ficam fora desta etapa: IF no runtime (E9.2); ETL (E9.1) além do consumo dos
artefatos; emenda final de relatório/roteiro (E9.4); MLP sklearn como AE.

## ADRs aplicáveis

- [ADR 0029 — Vitais ML híbrido](../../docs/adr/0029-vitais-ml-hibrido.md)
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md)

## Cenários de aceitação

### Cenário 1 — Notebook executável localmente

**Dado** env ML documentado e dados processados (ou amostra)  
**Quando** executar o notebook de ponta a ponta  
**Então** há treino com ≥1 epoch registrada e curva de loss  
**E** export de pesos é opcional e documentado.

### Cenário 2 — Isolamento do runtime

**Dado** o código em `backend/app/`  
**Quando** buscar imports de `torch`  
**Então** não há uso no caminho do worker/API.

### Cenário 3 — CI intacto

**Dado** o workflow CI  
**Quando** rodar a pipeline  
**Então** não instala PyTorch nem executa o notebook AE.

## Critérios de pronto (DoD E9.3)

- [ ] Spec SDD aprovada (esta).
- [ ] Notebook AE + `requirements-ml` (ou equivalente) + README notebooks.
- [ ] Export documentado; pesos grandes fora do Git se necessário.
- [ ] Zero `torch` no backend/Docker de produção.

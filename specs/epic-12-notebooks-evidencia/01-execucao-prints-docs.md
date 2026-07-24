# Épico 12 — Evidência visual dos notebooks (execução + docs)

## Objetivo

Rodar **localmente** os notebooks de evidência já versionados, capturar
**prints** e publicá-los na documentação (`docs/notebooks/images/` + índices),
para a banca/demo ver o resultado sem precisar reexecutar Jupyter no momento da
avaliação.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Spec pronta (T12.0)** — execução dos notebooks e prints nas tarefas T12.1–T12.2.

## Escopo

- Executar ponta a ponta (local, sem CI) os notebooks:
  1. `notebooks/eda_vitals_inicial.ipynb`
  2. `notebooks/eda_vitals_final.ipynb`
  3. `notebooks/evidencia_modalidades.ipynb`
  4. `notebooks/compare_vitals_ml.ipynb` (env backend / sklearn)
  5. `notebooks/train_vitals_autoencoder.ipynb` (env ML / `requirements-ml.txt`)
- Capturar PNGs leves em `docs/notebooks/images/` (nomes estáveis abaixo).
- Atualizar `notebooks/README.md` com seção “Evidência visual” e as imagens.
- Atualizar índices: `docs/README.md`, menção curta em
  `docs/relatorio-fase4.md` §5.3 (1–2 figuras: comparação + curva AE).
- TDD leve: testes que os PNGs existem e os READMEs referenciam os caminhos
  (sem executar Jupyter no CI).

### Layout dos prints

```text
docs/notebooks/images/
  01-eda-vitals-inicial.png
  02-eda-vitals-final.png
  03-evidencia-modalidades.png
  04-compare-vitals-ml.png
  05-autoencoder-loss.png
```

### Ambientes

| Env | Uso |
| --- | --- |
| Backend (`cd backend && uv sync --frozen`) | notebooks 1–4 |
| `.venv-ml` + `pip install -r notebooks/requirements-ml.txt` | notebook 5 (AE) |

Ficam fora desta etapa: alterar engines/runtime; treinar/regerar
`isolation_forest.joblib`; baixar Kaggle/PhysioNet; `gerar-evidencia-real.sh`
(áudio/vídeo); Torch na imagem API; Playwright; novas features de UI; PDF do
challenge.

## ADRs aplicáveis

- [ADR 0029 — Vitais ML híbrido](../../docs/adr/0029-vitais-ml-hibrido.md)
  (AE só evidência)
- [ADR 0030 — IA real opt-in + evidência](../../docs/adr/0030-ia-real-opt-in-evidencia.md)
  (prova fora do CI; artefatos versionados)
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md)

## Cenários de aceitação

### Cenário 1 — Notebooks executáveis localmente

**Dado** env A (backend) e env B (ML) documentados  
**Quando** executar os cinco notebooks na ordem do escopo  
**Então** cada um completa sem erro fatal  
**E** o AE registra ≥1 epoch e exibe curva de loss  
**E** a comparação emite precision/recall/agreement (AE pode ser *skipped*
sem Torch no env A).

### Cenário 2 — Prints versionados

**Dado** saídas bem-sucedidas dos notebooks  
**Quando** salvar os cinco PNGs em `docs/notebooks/images/`  
**Então** os arquivos existem com os nomes canônicos  
**E** não contêm secrets (`.env`, JWT, chaves).

### Cenário 3 — Docs apontam as imagens

**Dado** os PNGs no Git  
**Quando** ler `notebooks/README.md` e o índice em `docs/README.md`  
**Então** há links/embeds para a evidência visual  
**E** o relatório §5.3 cita pelo menos a comparação e/ou a curva AE.

### Cenário 4 — CI intacto

**Dado** o workflow CI  
**Quando** inspecionar jobs  
**Então** o CI **não** instala Jupyter/Torch nem executa os notebooks  
**E** os testes novos só checam presença de arquivos/links.

## Tarefas planejadas (uma por commit)

| Tarefa | Conteúdo |
| ------ | -------- |
| T12.0 | Esta spec + linha no índice `docs/README.md` (docs only) — **feita** |
| T12.1 | Executar notebooks 1–5 localmente + gravar os 5 PNGs |
| T12.2 | Emendar READMEs + relatório §5.3 + testes de presença dos prints |

Branch: `feature/limen-epic-12-notebooks-evidencia` a partir de `main`.

## Critérios de pronto (DoD E12)

- [x] Spec SDD aprovada (esta).
- [ ] Cinco notebooks executados com sucesso (evidência local do autor).
- [ ] Cinco PNGs em `docs/notebooks/images/` commitados.
- [ ] `notebooks/README.md` + `docs/README.md` (+ §5.3) atualizados.
- [ ] Testes de presença verdes; CI sem Jupyter/Torch.
- [ ] Sem alteração de runtime ML; sem download de dataset no CI.

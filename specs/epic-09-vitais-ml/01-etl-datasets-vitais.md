# Épico 9 — ETL offline de datasets de vitais (E9.1)

## Objetivo

Definir o contrato do **ETL offline** que transforma amostras de datasets
públicos no schema/features usados para treinar o Isolation Forest e alimentar
o notebook do autoencoder — **sem** tornar download dependência de CI, smoke ou
API.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída (T9.1)** — script ETL + READMEs; fixtures sintéticas intactas;
sem download no CI. Treino IF / AE ficam nas tarefas seguintes.

## Escopo

- Documentar e implementar script(s) sob `scripts/` que:
  - leem brutos opcionais em `data/raw/` (gitignored);
  - normalizam para o schema Limen (ou features derivadas documentadas);
  - produzem artefatos de treino/validação sob caminhos versionáveis
    (ex.: `data/processed/vitals/` gitignored ou amostras mínimas documentadas).
- Fontes primárias:
  - Human vital signs (Kaggle);
  - amostra Hospital Deterioration;
  - PhysioNet: **somente citação** (sem parse obrigatório).
- README curto em `data/raw/` ou `data/processed/vitals/` com URLs, licença
  resumida e comando de regeneração.
- Manter fixtures sintéticas atuais intactas para TDD/demo
  ([ADR 0008](../../docs/adr/0008-vitais-sinteticos.md)).

Ficam fora desta etapa: plugar IF no worker; treino PyTorch; alteração do CI
para baixar Kaggle; PHI real; modalidades vídeo/áudio.

## ADRs aplicáveis

- [ADR 0029 — Vitais ML híbrido](../../docs/adr/0029-vitais-ml-hibrido.md)
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md)
- [ADR 0001 — Privacidade](../../docs/adr/0001-privacidade-paciente.md)

## Layout esperado

```text
data/raw/                      # gitignored — brutos Kaggle/Deterioration
data/processed/vitals/         # gitignored ou amostras mínimas documentadas
scripts/etl_vitals_datasets.py # (nome final na implementação)
models/vitals/                 # reservado ao IF (spec 02) — não treinar aqui
```

## Cenários de aceitação

### Cenário 1 — Sem brutos, repo clonável

**Dado** clone limpo sem `data/raw/`  
**Quando** subir Compose / rodar pytest / smoke vitais  
**Então** tudo funciona como no baseline (fixtures sintéticas).

### Cenário 2 — Com brutos locais

**Dado** brutos colocados conforme o README  
**Quando** executar o script de ETL documentado  
**Então** surgem arquivos processados no schema/features documentados  
**E** o script é determinístico o bastante para repetir o treino (seed fixo).

### Cenário 3 — Sem download no CI

**Dado** o workflow de CI atual  
**Quando** inspecionar jobs  
**Então** não há passo que baixe Kaggle/PhysioNet/HuggingFace.

## Critérios de pronto (DoD E9.1)

- [x] Spec SDD aprovada (esta).
- [x] Script ETL + README de `data/raw`/`processed` commitados.
- [x] Fixtures sintéticas e testes atuais intactos.
- [x] Nenhuma dependência nova obrigatória no `Dockerfile` do backend.
- [x] ADR 0029 referenciada; sem download ao vivo na API.

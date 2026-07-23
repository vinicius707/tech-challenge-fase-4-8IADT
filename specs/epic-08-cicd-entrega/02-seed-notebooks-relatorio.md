# CI/CD e entrega — Seed, notebooks, relatório e roteiro (E8.2)

## Objetivo

Fechar a **entrega acadêmica** da Fase 4: seed demo documentado ponta a ponta,
notebooks finais de evidência, relatório com capítulo de datasets, roteiro do
vídeo de demonstração e README operacional de entrega (incluindo consumo das
imagens GHCR quando aplicável).

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Status da entrega

**Concluída em 22 de julho de 2026** (T8.5–T8.8: seed HTTP Compose, notebooks
finais, relatório + roteiro, README de entrega e fechamento do Épico 8).

## Escopo

### Seed demo

- Documentar (e endurecer se necessário) o caminho Compose +
  [`scripts/seed_multimodal_demo.py`](../../scripts/seed_multimodal_demo.py)
  (e/ou seed via API HTTP) para obter ao menos um Caso demo com modalidades
  `vitals`, `video`, `audio` e `prescriptions`, idempotente o bastante para
  repetir a demo.
- Instruções claras no README: pré-requisitos, credenciais seed, ordem
  `up` → seed → UI/API.
- Não substituir o smoke de E8.1 (só vitais); o seed multimodal é para demo
  humana / evidência, não gate obrigatório de CI pesado.

### Notebooks finais

- Evoluir / complementar o notebook EDA inicial
  ([`notebooks/eda_vitals_inicial.ipynb`](../../notebooks/eda_vitals_inicial.ipynb))
  com notebooks finais sob `notebooks/` que documentem calibração, faixas e
  evidência das modalidades conforme o catálogo (sem download obrigatório no
  CI).
- Brutos grandes continuam fora do Git (`.gitignore`); notebooks citam URL e
  como regenerar fixtures/samples.

### Relatório

- Relatório da Fase 4 (Markdown e/ou PDF gerado a partir de fonte versionada
  em `docs/` — caminho final na implementação) contendo, no mínimo, um
  **capítulo de datasets** com:
  - Human vital signs (Kaggle)
  - Hospital Deterioration Dataset
  - PhysioNet (Challenge 2019 e/ou MC-MED — referência metodológica)
  - AudioSet (referência de áudio)
  - Demais entradas do catálogo canônico do plano (Medical Speech, 3DYoga90 /
    stock CC, prescricões sintéticas) citadas de forma consistente com
    `data/fixtures/` e `data/samples/`.
- Disclaimer explícito: protótipo acadêmico, não dispositivo médico.
- Escopo técnico alinhado aos épicos 1–8 (arquitetura, privacidade, fila,
  modalidades, UI/a11y, CI/CD).

### Roteiro de vídeo

- Documento curto (ex.: `docs/demo/roteiro-video.md`) com passos cronológicos
  da demo gravada: login → Paciente → Caso (vitais ± multimodal) → Risco /
  Justificativa / Alertas → (opcional) DLQ admin → menção a smoke/GHCR.
- Duração-alvo e o que **não** mostrar (secrets, PHI real).

### README de entrega

- Atualizar [`README.md`](../../README.md) (e índice
  [`docs/README.md`](../../docs/README.md)) para:
  - Como puxar/rodar com imagens GHCR (quando E8.1 estiver pronto) **ou**
    build local Compose.
  - Smoke fundação + smoke Caso vitais + seed multimodal.
  - Links para relatório, notebooks, roteiro e specs do Épico 8.
  - Remover/atualizar o trecho “ainda não fazem parte… Épico 8”.

Ficam fora desta etapa: novas features de produto; gate Lighthouse novo;
Azure Speech real obrigatório no CI; publish GHCR / smoke vitais (E8.1);
E2E Playwright; deploy cloud.

## ADRs aplicáveis

- [ADR 0028 — CI/CD Actions + GHCR](../../docs/adr/0028-cicd-actions-ghcr.md):
  CD da demo = Compose + imagens GHCR; sem deploy cloud automático.
- [ADR 0008 — Vitais sintéticos](../../docs/adr/0008-vitais-sinteticos.md):
  datasets públicos no relatório/notebooks, não no runtime crítico.
- [ADR 0010 — Prescrições](../../docs/adr/0010-prescricoes-regras-historico.md)
  / specs E6.3: seed multimodal já existente como base.
- [ADR 0001 — Privacidade](../../docs/adr/0001-privacidade-paciente.md):
  demo e relatório sem PHI real.
- [ADR 0012 — Nome Limen](../../docs/adr/0012-nome-limen.md)

Nenhuma decisão nova de arquitetura identificada. Se o formato do relatório
(PDF obrigatório vs só Markdown) for imposto pelo enunciado da disciplina de
forma que exija tooling novo, registrar emenda pontual ou ADR só se mudar
contrato de entrega — caso contrário Markdown versionado basta nesta fase.

## Catálogo de datasets (capítulo do relatório)

| Papel | Dataset | Uso no E8.2 |
| ----- | ------- | ----------- |
| Vitais (Kaggle) | Human vital signs | Cap. datasets + notebooks |
| Deterioração | Hospital Deterioration | Cap. datasets + notebooks |
| PhysioNet | Challenge 2019 / MC-MED | Cap. datasets (referência; sem runtime) |
| Áudio (ref.) | AudioSet | Cap. datasets |
| Áudio (demo) | Medical Speech | Citação + samples já em `data/samples/` |
| Vídeo fisio | 3DYoga90 / gravação | Citação + samples |
| Vídeo cirurgia leve | Stock CC | Citação no README/samples |
| Prescrições | Sintético Limen | `data/fixtures/prescriptions/` |

URLs canônicas: plano
[`.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md`](../../.cursor/plans/arquitetura_multimodal_fase_4_a1c92623.plan.md)
e specs E3.0 / E6.*.

## Cenários de aceitação

### Cenário 1 — Seed demo reproduzível

**Dado** Compose no ar com Operadores seed  
**Quando** seguir o README e executar o seed multimodal documentado  
**Então** existe ao menos um Caso com Artefatos das quatro modalidades  
**E** reexecutar o seed não quebra a demo (idempotência / chaves documentadas).

### Cenário 2 — Notebooks finais

**Dado** o diretório `notebooks/` no repo  
**Quando** abrir os notebooks finais  
**Então** há evidência de EDA/calibração e referência aos datasets do catálogo  
**E** não há dependência de download de brutos no CI.

### Cenário 3 — Capítulo de datasets no relatório

**Dado** o relatório versionado da Fase 4  
**Quando** ler o capítulo de datasets  
**Então** constam Kaggle Vital Signs, Hospital Deterioration, PhysioNet e
AudioSet (e demais do catálogo de forma consistente)  
**E** fica explícito o que é fixture/runtime vs referência metodológica.

### Cenário 4 — Roteiro de vídeo

**Dado** o documento de roteiro  
**Quando** um apresentador seguir os passos  
**Então** a demo cobre login → Caso → Risco/Alertas (estrelas da UI)  
**E** o roteiro indica o que omitir (secrets, PHI).

### Cenário 5 — README de entrega

**Dado** um avaliador com Docker  
**Quando** seguir só o README raiz  
**Então** consegue subir a stack (build local e/ou imagens GHCR), rodar smokes
documentados e localizar relatório/notebooks/roteiro/specs.

## Critérios de pronto (DoD desta etapa E8.2)

- [x] Spec SDD aprovada e versionada (esta).
- [x] Seed demo Compose documentado (e ajustado se necessário).
- [x] Notebooks finais commitados sob `notebooks/`.
- [x] Relatório com capítulo de datasets (catálogo mínimo acima).
- [x] Roteiro de vídeo versionado.
- [x] README + `docs/README.md` de entrega atualizados; menção “Épico 8
      pendente” removida/atualizada.
- [x] Sem novas features de produto; sem Azure obrigatório no CI; sem E2E UI.

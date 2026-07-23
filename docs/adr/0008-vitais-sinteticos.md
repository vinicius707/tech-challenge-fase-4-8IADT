# Sinais vitais sintéticos com datasets de referência

A detecção de anomalias em sinais vitais usa séries sintéticas geradas com faixas fisiológicas e anomalias injetadas (reprodutível para testes e demo). Datasets públicos (PhysioNet, Kaggle) entram como referência metodológica e eventual amostra ilustrativa no relatório — não como dependência de runtime. Alternativa rejeitada: pipeline obrigatório de download/parse PhysioNet no caminho crítico da demo.

## Emenda (Épico 9)

Trilho opcional de ML documentado em
[ADR 0029 — Vitais ML híbrido](0029-vitais-ml-hibrido.md): ETL offline +
Isolation Forest atrás de `LIMEN_VITALS_BACKEND` (CI permanece em `thresholds`)
+ autoencoder PyTorch só em notebook/export. Fixtures sintéticas e o default
de runtime **não** são removidos.

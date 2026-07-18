# Sinais vitais sintéticos com datasets de referência

A detecção de anomalias em sinais vitais usa séries sintéticas geradas com faixas fisiológicas e anomalias injetadas (reprodutível para testes e demo). Datasets públicos (PhysioNet, Kaggle) entram como referência metodológica e eventual amostra ilustrativa no relatório — não como dependência de runtime. Alternativa rejeitada: pipeline obrigatório de download/parse PhysioNet no caminho crítico da demo.

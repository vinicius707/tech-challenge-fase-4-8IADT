# Gráficos: Recharts com lazy load

Tendência de Risco e Séries Vitais usam Recharts, carregado via `next/dynamic` apenas em `/pacientes/[id]` e `/casos/[id]`. Demais rotas não incluem a lib no bundle inicial. Componentes centralizados em um módulo `charts/`. Motivo: DX adequado para 2 gráficos sem penalizar login/listas. Alternativas rejeitadas: SVG manual; uPlot; carregar Recharts no layout global.

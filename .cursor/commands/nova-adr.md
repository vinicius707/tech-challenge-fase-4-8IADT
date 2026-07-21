---
description: Registra uma decisão de arquitetura como ADR numerada em docs/adr.
---

# Nova ADR

Use quando surgir uma decisão de arquitetura nova (a regra exige registrar antes de codar).
Argumento: título curto da decisão.

1. Descubra o próximo número olhando `docs/adr/` (maior `NNNN` + 1, com 4 dígitos).
2. Crie `docs/adr/NNNN-slug-curto.md` seguindo o estilo enxuto das ADRs existentes:
   contexto/decisão em prosa curta e uma linha de "Alternativas rejeitadas".
3. Adicione a ADR ao índice em `docs/README.md` na seção apropriada.
4. Se a decisão emenda/supersede uma ADR anterior, anote isso no próprio arquivo antigo
   (não renumere ADRs — a numeração é estável).
5. Mostre o caminho do arquivo criado. O commit da ADR entra junto da tarefa relacionada
   via `/finalizar-tarefa`.

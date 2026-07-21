---
description: Executa UMA tarefa do épico atual em SDD → TDD, com escopo fechado.
---

# Executar tarefa

Siga a regra `fluxo-epicos-tarefas`. Argumento: id/descrição da tarefa (ex.: `T3.1`).

1. Confirme a branch atual `feature/limen-epic-XX-...` (senão, rode `/iniciar-epico`).
2. Releia na spec **somente** o trecho desta tarefa e o escopo do épico.
3. **Escopo fechado**: faça apenas o descrito nesta tarefa. Nada de outras tarefas,
   refactors extras ou o que está em "Ficam fora desta etapa". Se faltar informação
   ou surgir decisão de arquitetura, **pare e pergunte** (registre ADR se for o caso).
4. TDD: escreva/ajuste os testes primeiro (`backend/tests/`), depois implemente
   o mínimo para passar.
5. Valide localmente:

```bash
cd backend && uv sync --frozen && uv run python -m compileall -q app migrations tests && uv run pytest
```

6. Se passar, **pare** e me mostre um resumo do que mudou. Para gravar, use `/finalizar-tarefa`.
   Não abra a próxima tarefa nesta sessão.

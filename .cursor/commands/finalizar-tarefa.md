---
description: Encerra a tarefa — valida, faz UM commit no padrão, dá push e pede nova sessão.
---

# Finalizar tarefa

Siga a regra `fluxo-epicos-tarefas`. Argumento (opcional): mensagem do commit.

1. Rode a validação e só continue se **tudo passar**:

```bash
cd backend && uv sync --frozen && uv run python -m compileall -q app migrations tests && uv run pytest
```

2. Atualize os docs que a spec exigir (`docs/README.md`, `.env.example`, `README.md`).
3. Faça **um único commit** cobrindo apenas esta tarefa, com mensagem em português,
   no imperativo, capitalizada e com ponto final (sem prefixo tipo `feat:`):

```bash
git add -A
git commit -m "Mensagem no padrão do projeto."
git push -u origin HEAD
```

   Obs.: o guardrail bloqueia commit/push em `main`/`master`; confirme estar em `feature/...`.
4. Mostre o resumo do commit (`git log -1 --oneline`) e o status do push.
5. **Encerre a sessão aqui**: peça para eu abrir uma **nova sessão** para a próxima
   tarefa/épico, preservando a janela de contexto. Não comece a próxima tarefa agora.

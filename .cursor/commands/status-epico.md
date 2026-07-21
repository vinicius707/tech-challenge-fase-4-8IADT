---
description: Mostra o estado do épico atual — branch, spec, tarefas feitas/pendentes e próximo passo.
---

# Status do épico

Use no início de cada sessão nova para retomar o contexto sem reler tudo.
Siga a regra `fluxo-epicos-tarefas`. Não implemente nada aqui — só diagnostique.

1. Estado do git (branch, se está limpo, e sincronia com o remoto):

```bash
git rev-parse --abbrev-ref HEAD
git status -sb
git log --oneline -5
```

2. Identifique o épico pela branch (`feature/limen-epic-XX-...`) e abra a spec
   correspondente em `specs/epic-XX-*/`.
3. A partir da spec e dos commits recentes, monte um resumo curto:
   - Épico e spec em uso.
   - Tarefas já concluídas (commits) vs. tarefas pendentes.
   - "Ficam fora desta etapa" (para reforçar o escopo fechado).
   - ADRs aplicáveis ainda abertas, se houver.
4. Termine indicando **a próxima tarefa** e sugerindo `/executar-tarefa TX.Y`.

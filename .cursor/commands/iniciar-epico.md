---
description: Inicia um épico — valida/cria a spec e abre a branch feature/limen-epic-XX-nome.
---

# Iniciar épico

Siga a regra `fluxo-epicos-tarefas`. Argumento (opcional): número/nome do épico.

1. Identifique o épico alvo (a partir do argumento ou me pergunte qual é).
2. Confirme que existe a spec em `specs/epic-XX-nome/` com contratos Given/When/Then
   e a seção "Ficam fora desta etapa". Se não existir ou estiver incompleta,
   **pare e proponha a spec primeiro** — não comece a implementar sem spec aprovada.
3. Liste as ADRs aplicáveis citadas pela spec e verifique se há decisão nova pendente;
   se houver, registre com `/nova-adr` antes de codar.
4. Atualize a `main` local e crie a branch:

```bash
git checkout main && git pull --ff-only
git checkout -b feature/limen-epic-XX-nome-curto
```

5. Proponha a quebra do épico em tarefas pequenas (`TX.0`, `TX.1`, …), cada uma = um commit.
6. **Pare aqui** e liste as tarefas. Não implemente ainda; use `/executar-tarefa` para a primeira.

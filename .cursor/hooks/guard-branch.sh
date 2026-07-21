#!/bin/bash
# Guardrail do fluxo de épicos/tarefas: protege branches e reforça o padrão feature/.
# Fail-open: qualquer erro inesperado deixa o comando seguir (permission allow).

set -u

allow() { printf '{"permission":"allow"}\n'; exit 0; }

input=$(cat 2>/dev/null) || allow
command=$(printf '%s' "$input" | jq -r '.command // empty' 2>/dev/null) || allow

# Só age em git commit / git push.
case "$command" in
  *"git commit"*|*"git push"*) : ;;
  *) allow ;;
esac

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || allow
[ -z "$branch" ] && allow

# Bloqueia commit/push direto em branches protegidas.
case "$branch" in
  main|master|develop)
    printf '{"permission":"deny","user_message":"Commit/push direto em \\"%s\\" é proibido. Crie uma branch feature/limen-epic-XX-nome.","agent_message":"Guardrail: não commite em %s. Crie e use uma branch feature/... antes de continuar."}\n' "$branch" "$branch"
    exit 0
    ;;
esac

# Fora do padrão feature/... pede confirmação em vez de bloquear (permite hotfix/, etc.).
case "$branch" in
  feature/*) allow ;;
  *)
    printf '{"permission":"ask","user_message":"Branch \\"%s\\" foge do padrão feature/limen-epic-XX-nome. Confirmar mesmo assim?","agent_message":"Guardrail: branch %s não segue o padrão feature/... esperado pelo fluxo do projeto."}\n' "$branch" "$branch"
    exit 0
    ;;
esac

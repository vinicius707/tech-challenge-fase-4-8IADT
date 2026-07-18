# Estado no frontend: TanStack Query + Zustand (sessão)

Server state (Casos, Pacientes, Alertas, Falhas, polling de `processing`) fica no TanStack Query. Sessão do Operador (JWT, papel, preferências mínimas de UI) fica no Zustand. Estado efêmero de componentes permanece em `useState`. SSE invalida/atualiza queries — não vira store global. Motivo: hábito do time com Zustand para sessão, sem colocar dados da API no Zustand (evita dual source of truth). Alternativa rejeitada: Redux; Query+Context only (válida, mas não escolhida).

# Autorização na API: JWT com papéis, worker fora do HTTP

A API exige JWT em todas as rotas exceto `/health` e `/auth/login`. Papel `medico` cobre Pacientes, Casos, Alertas e desmascarar Rótulo Sensível; `admin` inclui Falhas de Processamento e métricas operacionais. O worker RQ acessa Postgres, Redis e MinIO diretamente — não autentica via HTTP da API. RQ Dashboard permanece ferramenta de Compose, fora do perímetro do produto. Alternativas rejeitadas: API keys de serviço para o worker; dashboard sem restrição de rede em “prod” demo.

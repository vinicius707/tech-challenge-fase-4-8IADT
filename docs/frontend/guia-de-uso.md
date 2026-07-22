# Guia de uso — Frontend Limen (Épico 4)

Documentação operacional e visual do shell Next.js: login, Pacientes, Novo Caso
de vitais e detalhe de Caso com Risco/Alerta.

> O Limen é um **protótipo acadêmico** e **não é um dispositivo médico**. Não use
> para decisões clínicas reais.

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Subir a aplicação](#subir-a-aplicação)
3. [Credenciais demo](#credenciais-demo)
4. [Mapa de rotas](#mapa-de-rotas)
5. [Fluxo guiado (com prints)](#fluxo-guiado-com-prints)
6. [Arquitetura da UI (resumo)](#arquitetura-da-ui-resumo)
7. [Fixtures de vitais](#fixtures-de-vitais)
8. [Regenerar prints](#regenerar-prints)
9. [Troubleshooting](troubleshooting.md)

## Pré-requisitos

| Item | Notas |
| ---- | ----- |
| Docker Desktop / Engine + Compose v2 | Portas livres: 3000, 5432, 6379, 8000, 9000, 9001 |
| Git | Clonar este repositório |
| (Opcional) Node 22+ | Só se for regenerar prints ou rodar `npm` fora do Compose |

## Subir a aplicação

Na raiz do repositório:

```bash
./scripts/start-limen.sh
```

O script:

1. Cria `.env` a partir de `.env.example` se ainda não existir
2. Executa `docker compose up -d --build --wait`
3. Valida API (`/health`), proxy da UI (`/api/health`) e `/login`
4. Imprime as URLs e as credenciais demo

Variantes:

```bash
./scripts/start-limen.sh --smoke   # sobe + smoke da fundação
./scripts/start-limen.sh --down    # encerra (mantém volumes)
./scripts/start-limen.sh --reset   # encerra e apaga Postgres/MinIO
```

URLs após o start:

| Recurso | URL |
| ------- | --- |
| UI | <http://localhost:3000> |
| Login | <http://localhost:3000/login> |
| API | <http://localhost:8000> |
| OpenAPI | <http://localhost:8000/docs> |
| MinIO Console | <http://localhost:9001> |

## Credenciais demo

Definidas no `.env` (valores padrão do `.env.example`):

| Papel | Usuário | Senha |
| ----- | ------- | ----- |
| Médico | `medico` | `medico_dev_only` |
| Admin | `admin` | `admin_dev_only` |

Neste épico, `medico` e `admin` usam as **mesmas telas** (sem UI de DLQ).

## Mapa de rotas

| Rota | Auth | Função |
| ---- | ---- | ------ |
| `/login` | pública | Formulário de login |
| `/` | autenticada | Início (shell) |
| `/pacientes` | autenticada | Lista + criar Paciente mínimo |
| `/pacientes/[id]` | autenticada | Detalhe (código + rótulo mascarado) |
| `/pacientes/[id]/novo-caso` | autenticada | Upload CSV de vitais |
| `/casos/[id]` | autenticada | Status, polling, Risco e Alertas |

Rotas futuras (desabilitadas na nav): `/alertas`, `/admin/falhas`.

## Fluxo guiado (com prints)

Os arquivos em [`images/`](images/) são capturas reais do shell. Se a pasta
estiver vazia no seu clone, regenere com a seção [Regenerar prints](#regenerar-prints).

### 1. Login

Abra <http://localhost:3000/login> (ou qualquer rota autenticada — o guard
redireciona para o login).

![Tela de login](images/01-login.png)

1. Informe usuário e senha demo (`medico` / `medico_dev_only`)
2. Clique em **Entrar**
3. Em sucesso, a sessão (access + refresh) fica no Zustand (`limen-session` no
   `localStorage`) e você vai para `/`

Erros comuns: credenciais inválidas; rate limit (`5/minute` no `.env`); backend
fora do ar (veja [troubleshooting](troubleshooting.md)).

### 2. Shell (Início)

![Shell autenticado — Início](images/02-inicio.png)

- Header com landmarks (`banner` / navegação / `main`)
- Username e papel do Operador
- Logout
- Nav: **Início** e **Pacientes** ativos; Alertas/Admin desabilitados neste épico
- Em viewport estreita, o menu colapsa (botão com `aria-expanded`)

### 3. Lista de Pacientes

Navegue para **Pacientes** ou <http://localhost:3000/pacientes>.

![Lista de Pacientes](images/03-pacientes.png)

- Tabela com código `PAC-NNN` e rótulo mascarado (ou `—`)
- **Novo Paciente** chama `POST /api/patients` (sem campos extras)
- **Abrir** leva ao detalhe

### 4. Detalhe do Paciente

![Detalhe do Paciente](images/04-paciente-detalhe.png)

- Código e Rótulo Sensível mascarado (reveal completo fica para épicos futuros)
- CTA **Novo Caso** → `/pacientes/{id}/novo-caso`
- A API ainda **não** lista Casos por Paciente; a lacuna está documentada na tela

### 5. Novo Caso (upload de vitais)

![Formulário Novo Caso](images/05-novo-caso.png)

1. Selecione um CSV de vitais (use as fixtures em `data/fixtures/vitals/`)
2. Clique em **Criar Caso**
3. O cliente gera uma `Idempotency-Key` nova a cada tentativa de submit
4. Em sucesso (201 ou replay 200), a UI navega para `/casos/{id}`

### 6. Detalhe do Caso (polling → Risco)

![Detalhe do Caso — status e timeout de UX](images/06-caso-detalhe.png)

Enquanto o status for `pending` ou `processing`:

- A UI faz polling a cada **2s**
- Exibe skeleton / “Processando Caso…”
- Após **120s** sem estado terminal, **pausa o polling** (timeout de UX) e
  sugere recarregar a página — como no print acima

Quando o worker concluir com `done`:

- Mostra `risk_score` e `risk_level` (`BAIXO` / `MEDIO` / `ALTO`)
- Lista Alertas (`level` + `version`) se existirem
- Se `BAIXO`, a seção de Alertas aparece vazia (“Nenhum Alerta”)

Se `failed`, a UI mostra aviso de falha (sem painel DLQ neste épico).

Se o Caso permanecer em `pending` após o timeout, veja
[troubleshooting — Caso não sai de pending](troubleshooting.md#7-caso-não-sai-de-pendingprocessing).

## Arquitetura da UI (resumo)

| Camada | Tecnologia | Papel |
| ------ | ---------- | ----- |
| App Router | Next.js 15 | Rotas e layout |
| Estilo | Tailwind + shadcn/ui | Componentes |
| Sessão | Zustand + persist | Access/refresh JWT |
| Server state | TanStack Query | Pacientes / Casos + polling |
| Proxy | `next.config` rewrite `/api/*` | Encaminha ao FastAPI (`BACKEND_URL`) |

ADRs: [0023](../adr/0023-frontend-nextjs.md), [0024](../adr/0024-ui-tailwind-shadcn.md),
[0025](../adr/0025-estado-query-zustand.md), [0026](../adr/0026-rotas-frontend.md).

Baseline Lighthouse (sem gate): [`../perf/baseline/`](../perf/baseline/).

## Fixtures de vitais

| Arquivo | Expectativa típica após o worker |
| ------- | -------------------------------- |
| `data/fixtures/vitals/vitals_normal.csv` | `BAIXO`, sem Alerta |
| `data/fixtures/vitals/vitals_medium.csv` | `MEDIO`, Alerta v1 |
| `data/fixtures/vitals/vitals_high.csv` | `ALTO`, Alerta v1 |

O processamento depende do `worker` RQ e do `outbox-reconciler` no Compose.

## Regenerar prints

Com a stack no ar:

```bash
./scripts/start-limen.sh
node docs/frontend/scripts/capture-screenshots.mjs
```

Saída em `docs/frontend/images/01-login.png` … `06-caso-detalhe.png`.

Requer Chrome/Chromium e as devDependencies do frontend (`puppeteer-core`,
`chrome-launcher`).

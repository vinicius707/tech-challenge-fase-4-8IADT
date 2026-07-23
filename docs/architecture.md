# Arquitetura do Limen

Visão atual da stack após os **Épicos 1–6** (Fundação → Modalidades PDF).
Decisões numeradas vivem em [`adr/`](adr/); glossário em [`../CONTEXT.md`](../CONTEXT.md).

> O Limen é um protótipo acadêmico e **não** é um dispositivo médico.

## Conteúdo

1. [Containers (Compose)](#1-containers-compose)
2. [Fluxo de um Caso multimodal](#2-fluxo-de-um-caso-multimodal)
3. [Filas RQ (`default` / `video`)](#3-filas-rq-default--video)
4. [Fusão de Risco e falha parcial](#4-fusão-de-risco-e-falha-parcial)
5. [Provedor de Áudio (Azure F0)](#5-provedor-de-áudio-azure-f0)
6. [Prescrições (regras + histórico)](#6-prescrições-regras--histórico)
7. [Mapa de épicos](#7-mapa-de-épicos)

---

## 1. Containers (Compose)

Stack local: Next.js (UI) → FastAPI (API) → Postgres / Redis / MinIO; workers RQ
e reconciler de outbox.

```mermaid
flowchart TB
  subgraph clients [Clientes]
    Browser[Browser]
  end

  subgraph compose [Docker Compose]
    FE[frontend<br/>Next.js :3000]
    API[backend<br/>FastAPI :8000]
    WDEF[worker<br/>fila default]
    WVID[worker-video<br/>fila video]
    REC[outbox-reconciler]
    PG[(postgres)]
    RD[(redis)]
    MN[(minio<br/>bucket limen)]
  end

  Browser -->|HTTP / UI| FE
  Browser -->|HTTP / API opcional| API
  FE -->|rewrite /api/*| API
  API --> PG
  API --> RD
  API --> MN
  WDEF --> PG
  WDEF --> RD
  WDEF --> MN
  WVID --> PG
  WVID --> RD
  WVID --> MN
  REC --> PG
  REC --> RD
```

| Serviço | Papel |
| ------- | ----- |
| `frontend` | Shell Next (App Router); proxy `/api` → backend |
| `backend` | Auth JWT, Pacientes, Casos, upload de modalidades, admin DLQ |
| `worker` | Jobs `process_modality` nas filas leves (`default`) |
| `worker-video` | Jobs de `video` (CPU-heavy) |
| `outbox-reconciler` | Reenfileira outbox pendente (ADR 0016) |
| `postgres` | Domínio (Casos, Artefatos, Alertas, outbox, …) |
| `redis` | Broker RQ |
| `minio` | Blobs de Artefato (CSV, AVI, WAV, frames) |

---

## 2. Fluxo de um Caso multimodal

Criação com vitais e anexos posteriores (vídeo / áudio / prescriptions) usam
`Idempotency-Key`, gravam Artefato no MinIO e publicam job via outbox.

```mermaid
sequenceDiagram
  actor Medico
  participant UI as Frontend
  participant API as FastAPI
  participant PG as Postgres
  participant MN as MinIO
  participant OB as Outbox
  participant RQ as Redis RQ
  participant WK as Worker

  Medico->>UI: Novo Caso + CSV vitais
  UI->>API: POST /patients/{id}/cases + Idempotency-Key
  API->>MN: put Artefato vitals
  API->>PG: Caso + modality pending + outbox_jobs
  API->>OB: try_enqueue
  OB->>RQ: process_modality vitals default
  API-->>UI: 201 Caso

  WK->>RQ: dequeue
  WK->>MN: get CSV
  WK->>PG: modality done + fusão Risco/Alerta

  Medico->>UI: Anexa video / audio / prescriptions
  UI->>API: POST /cases/{id}/modalities/{m}
  API->>MN: put Artefato
  API->>PG: modality pending + outbox
  OB->>RQ: enqueue fila correta
  WK->>PG: done / failed + refundição
```

Modalidades suportadas hoje: `vitals`, `video`, `audio`, `prescriptions`.

Seed demo in-memory (quatro modalidades, keys fixas):
[`../scripts/seed_multimodal_demo.py`](../scripts/seed_multimodal_demo.py).

---

## 3. Filas RQ (`default` / `video`)

Isolamento de carga (ADR 0020): vídeo não monopoliza vitais/áudio/prescrições.

```mermaid
flowchart LR
  API[FastAPI / outbox] --> QV[fila video]
  API --> QD[fila default]

  QV --> WV[worker-video]
  QD --> WD[worker]

  WV -->|Pose / Scene| Risco[Fusão de Risco]
  WD -->|vitals / audio / prescriptions| Risco
```

| Modalidade | Fila | Timeout padrão |
| ---------- | ---- | -------------- |
| `vitals` | `default` | 30s |
| `audio` | `default` | 90s |
| `prescriptions` | `default` | 30s |
| `video` | `video` | 180s |

Timeouts configuráveis via `LIMEN_TIMEOUT_*_SECONDS` (ADR 0017).

---

## 4. Fusão de Risco e falha parcial

Cada modalidade termina em `done` / `failed` / `skipped`. O Caso pode fechar
`done` com falha parcial; a fusão só considera modalidades `done` (ADR 0013).

```mermaid
flowchart TB
  V[vitals done] --> F[fuse_done_modalities<br/>média dos scores]
  A[audio done] --> F
  Vid[video done] --> F
  P[prescriptions done] --> F
  X[modality failed] -.->|ignorada na fusão| F
  F --> R[Risco BAIXO / MEDIO / ALTO]
  R -->|≥ MEDIO| AL[Alerta versionado]
```

Reprocessamento seletivo: `POST /cases/{id}/reprocess` reenfileira só
`failed` e refundiciona.

---

## 5. Provedor de Áudio (Azure F0)

Resolução efetiva `azure` \| `local` \| `cache` (CONTEXT + ADR 0015). Cache
in-process por SHA-256 do payload; circuit breaker força `local` sem rede.

```mermaid
flowchart TD
  In[Artefato audio] --> Cache{SHA-256 no cache?}
  Cache -->|sim| ProvCache[provider=cache]
  Cache -->|não| CB{CB aberto ou<br/>AZURE_ENABLED=false?}
  CB -->|sim| Local[provider=local<br/>analyzer determinístico]
  CB -->|não| Azure[azure_analyze injetável]
  Azure -->|ok| ProvAz[provider=azure]
  Azure -->|falha| Local
  ProvAz --> Store[grava cache + modality done]
  Local --> Store
  ProvCache --> Done[badge no GET /cases/id]
  Store --> Done
```

CI/demo: `AZURE_ENABLED=false` (sem Azure real obrigatório).

---

## 6. Prescrições (regras + histórico)

Engine local (ADR 0010): dose / intervalo / medicamento inesperado + desvio
longitudinal vs. Casos anteriores do mesmo Paciente com `prescriptions` `done`.

```mermaid
flowchart TD
  CSV[CSV prescriptions] --> Rules[Regras do catálogo]
  Hist[Casos anteriores<br/>list_by_patient] --> Long[Desvio longitudinal<br/>dose / med novo]
  Rules --> Risk[ModalityRisk]
  Long --> Risk
  Risk --> Fuse[Fusão no Caso]
```

Fixtures: [`../data/fixtures/prescriptions/`](../data/fixtures/prescriptions/).

---

## 7. Mapa de épicos

```mermaid
flowchart LR
  E1[1 Fundação] --> E2[2 Identidade]
  E2 --> E3[3 Caso + fila]
  E3 --> E4[4 Shell UI]
  E4 --> E5[5 Resiliência]
  E5 --> E6[6 Modalidades]
  E6 --> E7[7 Alertas + polish]
  E7 --> E8[8 CI/CD + entrega]

  style E1 fill:#d4edda
  style E2 fill:#d4edda
  style E3 fill:#d4edda
  style E4 fill:#d4edda
  style E5 fill:#d4edda
  style E6 fill:#d4edda
  style E7 fill:#d4edda
  style E8 fill:#d4edda
```

| Épico | Status |
| ----- | ------ |
| 1–8 | Concluídos |

---

## Referências rápidas

| Documento | Conteúdo |
| --------- | -------- |
| [`README.md`](../README.md) | Operação local, curls, env |
| [`adr/`](adr/) | Decisões (0001–0028) |
| [`../specs/`](../specs/) | Contratos SDD por épico |
| [`../CONTEXT.md`](../CONTEXT.md) | Linguagem ubíqua |
| [`frontend/guia-de-uso.md`](frontend/guia-de-uso.md) | UI (Épico 4) |

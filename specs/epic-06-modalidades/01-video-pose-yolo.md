# Modalidades — Vídeo (Pose + YOLO)

## Objetivo

Entregar a modalidade `video` do Caso: samples versionados, processamento real
na fila RQ `video` (substituindo o stub do Épico 5), Análise Postural
(MediaPipe Pose) como foco e Detecção em Cena (YOLOv8 COCO + heurísticas)
como demo leve de cirurgia, com frames anotados no MinIO e contribuição ao
Risco do Caso.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.
> A parte cirúrgica é demonstração de visão computacional — sem fine-tune
> nem afirmação de análise clínica (ex.: sangramento).

## Status da entrega

**Pendente** (T6.0–T6.4 ok; falta T6.5–T6.6 desta etapa E6.1).

Etapas posteriores do Épico 6 (specs próprias no início de cada uma):

- E6.2 Áudio — Azure F0 + cache + fallback + CB + badge de provedor
- E6.3 Prescrições — regras + histórico + seed multimodal

## Escopo

- Fixtures/samples de vídeo pequenos versionados (ou regeneráveis) em
  `data/fixtures/video/`: ao menos **um** clip de fisioterapia/reabilitação
  (yoga/HAR/gravação 30–60s) e **um** clip stock CC de contexto cirúrgico leve.
- Catálogo de fontes no README das fixtures (3DYoga90 / gravação própria;
  stock CC documentado) — brutos grandes fora do Git.
- Extensão do contrato de Caso para aceitar upload de Artefato `video`
  (multipart) e enfileirar job `process_modality` na fila `video` (ADR 0020).
- Worker `worker-video`: processamento real (não stub):
  - **Análise Postural** (MediaPipe Pose) no cenário fisio → Anomalias de
    ângulo/estabilidade + frames-chave anotados no MinIO.
  - **Detecção em Cena** (YOLOv8 pré-treinado COCO) no cenário cirurgia leve →
    presença/ausência de pessoa/objetos genéricos + regras heurísticas
    documentadas (sem modelo clínico).
- Metadados de Artefato (vídeo original + frames) no Postgres; blobs no MinIO
  (ADR 0011).
- Modalidade `video` contribui ao Risco (fusão com vitais já existentes;
  falha parcial permanece válida).
- Timeouts de vídeo já previstos (ADR 0017 / Épico 5) aplicados ao job.
- TDD cobrindo: enqueue na fila `video`, Pose em fixture fisio, YOLO+heurística
  em fixture cirurgia, frames referenciados, Caso `done` com risco fundido.

Ficam fora desta etapa: áudio Azure F0 / badge de provedor (E6.2); prescrições
e seed multimodal completo (E6.3); UI de upload de vídeo polish/a11y (Épico 7);
Justificativa rica por template; SSE; fine-tune YOLO; detecção de sangramento
ou qualquer claim clínico cirúrgico; download obrigatório de datasets no CI;
Prometheus.

## ADRs aplicáveis

- [ADR 0007 — Escopo vídeo fisio + cirurgia leve](../../docs/adr/0007-escopo-video-fisio-cirurgia-leve.md)
- [ADR 0011 — Artefatos MinIO](../../docs/adr/0011-artefatos-minio.md)
- [ADR 0020 — Filas `video` / `default`](../../docs/adr/0020-filas-separadas-video.md)
- [ADR 0017 — Timeouts por modalidade](../../docs/adr/0017-timeouts-por-modalidade.md)
- [ADR 0013 — Falha parcial / reprocess](../../docs/adr/0013-falha-parcial-reprocessamento.md)
- [ADR 0016 — Outbox leve](../../docs/adr/0016-outbox-leve.md)
- [ADR 0018 — Idempotência](../../docs/adr/0018-idempotencia.md)

## Catálogo de fontes (calibração / fixtures)

| Papel | Fonte | URL / nota |
| ----- | ----- | ---------- |
| Fisio / postura | 3DYoga90 ou gravação própria 30–60s | https://github.com/seonokkim/3dyoga90 |
| Cirurgia leve | Stock CC (sem dataset de sangramento) | URL CC documentada no README das fixtures |

## Layout no repositório

```text
data/fixtures/video/           # clips curtos + README (schema, cenários, regeneração)
data/fixtures/video/README.md
# opcional: scripts/prepare_video_fixtures.py
```

## Contratos HTTP (mínimos)

### `POST /cases/{id}/modalities/video`

Anexa a modalidade `video` a um Caso existente (multipart do clip) com header
`Idempotency-Key`. Auth: Bearer (`medico` ou `admin`).

Resposta: Caso com modalidade `video` em `pending`/`processing` e Artefato
referenciando o objeto no MinIO. Replay idempotente com a mesma chave + mesmo
conteúdo → mesmo Caso; chave reutilizada com conteúdo diferente → `409`.

Caso inexistente → `404`. Sem `Idempotency-Key` → `400`.

### `GET /cases/{id}` (já existente)

Deve expor modalidade `video` (`done`/`failed`), Artefatos de vídeo/frames e
Risco fundido quando o Caso fechar.

## Cenários de aceitação

### Cenário 1 — Fisio na fila `video`

**Dado** um Caso com Artefato de vídeo fisio (fixture)  
**Quando** o worker da fila `video` processar a modalidade  
**Então** a modalidade `video` fica `done`  
**E** existem frames anotados (Pose) no MinIO referenciados como Artefatos  
**E** há ao menos uma Anomalia postural ou evidência explícita de estabilidade  
**E** o job **não** foi consumido apenas pelo worker `default`.

### Cenário 2 — Cirurgia leve (YOLO + heurística)

**Dado** um Caso com Artefato de vídeo stock cirúrgico  
**Quando** o worker processar com Detecção em Cena  
**Então** a modalidade `video` fica `done`  
**E** o resultado inclui classes COCO / flags heurísticas documentadas  
**E** não há claim de “sangramento” ou diagnóstico cirúrgico.

### Cenário 3 — Fusão com vitais (falha parcial intacta)

**Dado** Caso com `vitals` `done` e `video` `done`  
**Quando** a fusão ocorrer  
**Então** o Risco considera ambas as modalidades  
**E** se `video` falhar e `vitals` estiver `done`, o Caso ainda pode ficar `done`
(falha parcial do Épico 5).

### Cenário 4 — Auth

**Dado** ausência de sessão  
**Quando** enviar upload de vídeo  
**Então** `401`.

## Critérios de pronto (DoD desta etapa E6.1)

- [x] Spec SDD aprovada e versionada.
- [x] Fixtures vídeo + README de fontes/regeneração.
- [x] Upload → Artefato MinIO → job na fila `video`.
- [x] Pose (fisio) e YOLO+heurística (cirurgia leve) cobertos por TDD.
- [x] Frames anotados no MinIO; modalidade contribui ao Risco.
      *(frames Pose e scene; contribuição ao Risco via fusão)*
- [ ] Stub de `modality=video` do Épico 5 substituído por processamento real.
      *(Pose + cena/YOLO reais; fechamento worker/E2E = T6.5)*
- [ ] Sem áudio Azure real; sem UI polish de upload (Épico 7).

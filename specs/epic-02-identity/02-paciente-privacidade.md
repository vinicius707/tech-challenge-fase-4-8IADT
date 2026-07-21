# Identidade — Paciente, Rótulo Sensível e auditoria de reveal

## Objetivo

Definir o contrato mínimo de Paciente no Limen: identificação por código
pseudônimo, Rótulo Sensível opcional criptografado em repouso e mascarado por
padrão, revelação autenticada com Registro de Auditoria append-only, e exclusão
com cascata preparada para Casos e Artefatos futuros.

> O Limen é um protótipo acadêmico e não é um dispositivo médico.

## Escopo

- Modelo de Paciente com `código` público (`PAC-001`) e Rótulo Sensível opcional.
- CRUD HTTP de Paciente protegido por JWT (`medico` e `admin`).
- Criptografia Fernet do rótulo com `PII_ENCRYPTION_KEY` (nunca em claro no
  banco, logs ou respostas padrão).
- Respostas de listagem/detalhe com rótulo mascarado.
- `POST` de reveal que devolve o rótulo em claro e grava Registro de Auditoria.
- Migração Alembic das tabelas `patients` e `audit_records`.
- FKs futuras de Caso/Artefato com `ON DELETE CASCADE` documentadas e, quando
  a tabela de Caso ainda não existir, preparadas via comentário de schema /
  migração stub mínima acordada na implementação T2.6–T2.10.
- Documentação de `PII_ENCRYPTION_KEY` e rotação manual no `.env.example` /
  README.

Ficam fora desta etapa: frontend de Pacientes, Casos reais, upload de Artefatos,
tendência de risco, paginação avançada, busca full-text, consentimento LGPD
formal, retenção legal de auditoria, rotação automática de chave com
re-encrypt, Azure Key Vault e papéis além de `medico`/`admin`.

## ADRs aplicáveis

- [ADR 0001 — Privacidade do Paciente](../../docs/adr/0001-privacidade-paciente.md):
  código pseudônimo, rótulo criptografado/mascarado, sem CPF/prontuário real;
  exclusão remove Casos e Artefatos associados.
- [ADR 0005 — Chave PII em ambiente](../../docs/adr/0005-chave-pii-ambiente.md):
  Fernet/AES com `PII_ENCRYPTION_KEY` no ambiente; rotação manual.
- [ADR 0004 — Auth JWT e papéis](../../docs/adr/0004-auth-jwt-papeis.md) e
  [ADR 0021 — Autorização na API](../../docs/adr/0021-auth-api-papeis.md):
  rotas de Paciente exigem Bearer access token; `medico` e `admin` operam
  Pacientes e reveal nesta etapa (sem diferença de papel entre eles ainda).
- [ADR 0006 — Endurecimento de segurança](../../docs/adr/0006-endurecimento-seguranca.md):
  Registro de Auditoria obrigatório ao desmascarar Rótulo Sensível.
- [ADR 0009 — PostgreSQL + Redis](../../docs/adr/0009-postgres-redis.md):
  Pacientes e auditoria vivem no PostgreSQL.
- [ADR 0011 — Artefatos no MinIO](../../docs/adr/0011-artefatos-minio.md):
  exclusão de Paciente, nos épicos seguintes, deve remover também as chaves de
  Artefato referenciadas; nesta etapa apenas se prepara a cascata no schema.

## Modelo de domínio

**Paciente**

| Campo                         | Tipo                         | Notas                                              |
| ----------------------------- | ---------------------------- | -------------------------------------------------- |
| `id`                          | UUID                         | Chave interna                                      |
| `code`                        | string única                 | Código público, ex.: `PAC-001`                     |
| `sensitive_label_ciphertext`  | bytes/texto opcional         | Ciphertext Fernet; `NULL` se não houver rótulo     |
| `created_at`, `updated_at`    | timestamptz                  |                                                    |

Regras:

- Não existem campos de CPF, nome civil em claro, prontuário ou PHI real.
- O `code` é gerado pela API no create (sequencial `PAC-001`, `PAC-002`, …) e
  é **imutável** após a criação.
- O Rótulo Sensível é opcional no create/update; string vazia é tratada como
  ausência (`NULL` no banco).
- Em repouso só existe ciphertext; a chave nunca é persistida no banco.

**Rótulo Sensível (visão de API)**

| Visão        | Campo de resposta            | Valor                                              |
| ------------ | ---------------------------- | -------------------------------------------------- |
| Mascarada    | `has_sensitive_label`        | `true` / `false`                                   |
| Mascarada    | `sensitive_label_masked`     | `null` se ausente; `"********"` se presente        |
| Revelada     | `sensitive_label`            | texto em claro, só no endpoint de reveal           |

**Registro de Auditoria**

| Campo          | Tipo        | Notas                                              |
| -------------- | ----------- | -------------------------------------------------- |
| `id`           | UUID        |                                                    |
| `operator_id`  | UUID        | Operador autenticado que revelou                   |
| `patient_id`   | UUID        | Paciente alvo                                      |
| `action`       | string      | valor fixo nesta etapa: `reveal_sensitive_label`   |
| `created_at`   | timestamptz | instante do reveal                                 |

Regras:

- Append-only: a API **não** expõe update/delete de auditoria nesta etapa.
- Cada reveal bem-sucedido gera exatamente um registro.
- Reveal sem rótulo cadastrado **não** grava auditoria e responde `404` (ou
  `409` — ver contratos; a implementação deve seguir o contrato abaixo).

**Cascata (preparação)**

- `DELETE` de Paciente remove o Paciente e seus `audit_records`.
- Tabelas futuras (`cases`, metadados de Artefato) devem declarar
  `patient_id … ON DELETE CASCADE` (e limpeza de objetos no MinIO no épico de
  Casos). Nesta etapa, a migração documenta essa intenção; se for criada uma
  tabela stub de Caso só para fixar a FK, ela permanece vazia e fora da API.

## Autorização

Rotas desta etapa (todas protegidas):

| Método | Rota                                      | Papéis          |
| ------ | ----------------------------------------- | --------------- |
| `POST` | `/patients`                               | `medico`, `admin` |
| `GET`  | `/patients`                               | `medico`, `admin` |
| `GET`  | `/patients/{patient_id}`                  | `medico`, `admin` |
| `PATCH`| `/patients/{patient_id}`                  | `medico`, `admin` |
| `DELETE`| `/patients/{patient_id}`                 | `medico`, `admin` |
| `POST` | `/patients/{patient_id}/sensitive-label/reveal` | `medico`, `admin` |

Ausência/invalidade/expiração/blacklist do access token → `401 Unauthorized`.
Nesta etapa **não** há `403` por papel entre `medico` e `admin` nessas rotas
(a distinção de admin fica para Falhas de Processamento nos épicos seguintes).

## Contratos HTTP

Todas as rotas abaixo exigem `Authorization: Bearer <access_token>`.

### Representação mascarada (`PatientResponse`)

```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "code": "PAC-001",
  "has_sensitive_label": true,
  "sensitive_label_masked": "********",
  "created_at": "2026-07-21T16:00:00Z",
  "updated_at": "2026-07-21T16:00:00Z"
}
```

Sem rótulo:

```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "code": "PAC-002",
  "has_sensitive_label": false,
  "sensitive_label_masked": null,
  "created_at": "2026-07-21T16:00:00Z",
  "updated_at": "2026-07-21T16:00:00Z"
}
```

A resposta **nunca** inclui `sensitive_label`, ciphertext, nem a chave.

### `POST /patients`

Request:

```json
{
  "sensitive_label": "Paciente Demo"
}
```

`sensitive_label` é opcional. Omitido ou `null` → Paciente sem rótulo.

Sucesso `201 Created` → corpo `PatientResponse` mascarado, com `code` gerado
(`PAC-001` no primeiro Paciente do banco, depois incrementando o sufixo
numérico).

Erros:

- `401` sem/ inválido Bearer.
- `503` (ou `500` estável) se `PII_ENCRYPTION_KEY` estiver ausente/inválida
  **e** um rótulo tiver sido enviado. Create sem rótulo não depende da chave.

### `GET /patients`

Sucesso `200 OK`:

```json
{
  "items": [ /* PatientResponse… */ ]
}
```

Ordem: `code` ascendente. Paginação fica fora desta etapa.

### `GET /patients/{patient_id}`

Sucesso `200 OK` → `PatientResponse` mascarado.  
`patient_id` inexistente → `404` com `{"detail": "Paciente não encontrado"}`.

### `PATCH /patients/{patient_id}`

Request (parcial):

```json
{
  "sensitive_label": "Novo Rótulo"
}
```

- Enviar `sensitive_label` com texto → recriptografa e substitui.
- Enviar `sensitive_label: null` → remove o rótulo (`NULL` no banco).
- Omitir o campo → não altera o rótulo.
- Não é permitido alterar `code` ou `id`.

Sucesso `200 OK` → `PatientResponse` mascarado.  
Inexistente → `404`.

### `DELETE /patients/{patient_id}`

Sucesso `204 No Content`.  
Inexistente → `404`.  
Remove Paciente e `audit_records` associados (CASCADE).

### `POST /patients/{patient_id}/sensitive-label/reveal`

Sem corpo. Exige Bearer.

Sucesso `200 OK`:

```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "code": "PAC-001",
  "sensitive_label": "Paciente Demo",
  "revealed_at": "2026-07-21T16:05:00Z"
}
```

Efeitos colaterais obrigatórios:

1. Descriptografar com `PII_ENCRYPTION_KEY`.
2. Persistência de um `audit_records` com
   `action = "reveal_sensitive_label"`, `operator_id` do JWT e `patient_id`.

Erros:

- `401` sem/ inválido Bearer.
- `404` se o Paciente não existir **ou** se não houver rótulo
  (`{"detail": "Rótulo Sensível não disponível"}` neste segundo caso — a
  mensagem não deve vazar ciphertext).
- Falha de chave/ciphertext → `503`/`500` estável **sem** detalhe interno.

Não há endpoint público de listagem de auditoria nesta etapa; a existência do
registro é verificável nos testes TDD (store/consulta de apoio ao teste) e
ficará exposta em épicos futuros se necessário.

## Criptografia e configuração

Variáveis novas (documentar em `.env.example` e Compose):

- `PII_ENCRYPTION_KEY`: chave Fernet URL-safe base64 (gerar com
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
  Somente ambiente; nunca commitada com valor real.

Rotação manual (espelhar no README):

1. Pausar escritas de rótulo.
2. Introduzir a nova chave mantendo a anterior disponível para leitura
   transitória, se a implementação suportar dual-key; caso contrário,
   recriptografar todos os ciphertext com a nova chave em janela de manutenção.
3. Validar reveal e leituras mascaradas.
4. Remover a chave antiga.

Substituir a chave sem recriptografar torna rótulos existentes ilegíveis.

## Cenários de aceitação

### Cenário 1 — Criar Paciente com rótulo

**Dado** um Operador autenticado (`medico` ou `admin`) e `PII_ENCRYPTION_KEY`
válida  
**Quando** enviar `POST /patients` com `sensitive_label`  
**Então** a resposta deve ser `201`  
**E** deve incluir `code` no formato `PAC-NNN`, `has_sensitive_label: true` e
`sensitive_label_masked: "********"`  
**E** o corpo não deve conter o rótulo em claro nem o ciphertext  
**E** o banco deve persistir apenas ciphertext.

### Cenário 2 — Criar Paciente sem rótulo

**Dado** um Operador autenticado  
**Quando** enviar `POST /patients` sem `sensitive_label`  
**Então** a resposta deve ser `201`  
**E** `has_sensitive_label` deve ser `false` e `sensitive_label_masked` `null`.

### Cenário 3 — Listar e obter mascarado

**Dado** Pacientes cadastrados, com e sem rótulo  
**Quando** o cliente chamar `GET /patients` ou `GET /patients/{id}`  
**Então** todas as respostas devem usar a representação mascarada  
**E** nenhum rótulo em claro deve aparecer.

### Cenário 4 — Atualizar e remover rótulo

**Dado** um Paciente existente  
**Quando** `PATCH` enviar novo `sensitive_label`  
**Então** o máscara permanece e o ciphertext muda  
**Quando** `PATCH` enviar `sensitive_label: null`  
**Então** `has_sensitive_label` passa a `false`.

### Cenário 5 — Código imutável e sequencial

**Dado** nenhum Paciente no banco  
**Quando** forem criados dois Pacientes  
**Então** os códigos devem ser `PAC-001` e `PAC-002`  
**E** tentativas de alterar `code` via `PATCH` devem ser ignoradas ou rejeitadas
sem mudar o valor persistido.

### Cenário 6 — Reveal grava auditoria

**Dado** um Paciente com rótulo e um Operador autenticado  
**Quando** enviar `POST /patients/{id}/sensitive-label/reveal`  
**Então** a resposta deve ser `200` com `sensitive_label` em claro  
**E** deve existir exatamente um Registro de Auditoria com
`action = "reveal_sensitive_label"`, o `operator_id` do token e o `patient_id`.

### Cenário 7 — Reveal sem rótulo

**Dado** um Paciente sem rótulo  
**Quando** o cliente tentar reveal  
**Então** a resposta deve ser `404` com detalhe genérico de indisponibilidade  
**E** nenhum Registro de Auditoria deve ser criado.

### Cenário 8 — Rotas exigem JWT

**Dado** qualquer rota de Paciente desta spec  
**Quando** a chamada ocorrer sem `Authorization` ou com token inválido  
**Então** a resposta deve ser `401`.

### Cenário 9 — Exclusão em cascata da auditoria

**Dado** um Paciente com ao menos um Registro de Auditoria de reveal  
**Quando** enviar `DELETE /patients/{id}`  
**Então** a resposta deve ser `204`  
**E** o Paciente e seus `audit_records` não devem mais existir.

### Cenário 10 — Schema preparado para cascata de Caso

**Dado** a migração desta etapa aplicada  
**Quando** o schema for inspecionado  
**Então** a intenção `cases.patient_id → patients.id ON DELETE CASCADE` deve
estar materializada (tabela stub ou constraint documentada na migração seguinte
de Caso, conforme fatia T2.6–T2.10)  
**E** a exclusão de Paciente não deve deixar órfãos quando Casos existirem.

### Cenário 11 — Chave ausente bloqueia escrita de rótulo

**Dado** ambiente sem `PII_ENCRYPTION_KEY` válida  
**Quando** o cliente tentar criar/atualizar Paciente **com** rótulo  
**Então** a operação deve falhar de forma controlada  
**E** create/update **sem** rótulo e listagens mascaradas de Pacientes sem
rótulo devem continuar possíveis.

## Definição de pronto

- Spec aprovada como contrato antes da implementação T2.6–T2.10.
- Testes TDD cobrem CRUD mascarado, Fernet, reveal + auditoria, 401, exclusão
  com cascata de auditoria e preparação de FK CASCADE para Caso.
- `.env.example`, Compose e README documentam `PII_ENCRYPTION_KEY` e a rotação
  manual, sem secrets reais.
- Nenhuma resposta padrão de Paciente expõe PII em claro.
- Glossário de [`CONTEXT.md`](../../CONTEXT.md) respeitado: Paciente, Código do
  Paciente, Rótulo Sensível, Registro de Auditoria, Operador.

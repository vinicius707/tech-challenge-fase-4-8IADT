# Limen

Protótipo acadêmico (FIAP 8IADT Fase 4) de análise multimodal para detecção precoce de risco clínico a partir de vídeo, áudio e sinais vitais/prescrições. O nome **Limen** (limiar) refere-se ao ponto em que o Risco do Caso cruza os níveis BAIXO, MEDIO e ALTO.

## Language

**Paciente**:
Pessoa sob monitoramento clínico a quem os Casos pertencem; agrega histórico de análises. A tendência de risco é a série dos escores/níveis dos Casos ao longo do tempo (lista + gráfico), não um Risco separado do Paciente.
_Avoid_: Usuário, cliente, sujeito, person_id solto, cadastro com CPF/PHI real, risco agregado como entidade própria

**Código do Paciente**:
Identificador público pseudônimo exibido na UI (ex.: `PAC-001`), sem valor de identificação civil.
_Avoid_: CPF, prontuário real, nome completo como chave

**Rótulo Sensível**:
Campo opcional de exibição do Paciente (ex.: nome) armazenado criptografado em repouso e mascarado na interface.
_Avoid_: PII em texto claro, nome em logs

**Caso**:
Pacote pontual de evidências multimodais (vídeo, áudio, vitais e/ou prescrições) submetido para análise e fusão de risco em uma única execução, sempre vinculado a um Paciente. Exige ao menos uma modalidade; modalidades ausentes não entram na fusão (pesos renormalizados). Cada modalidade tem status próprio (`pending`/`processing`/`done`/`failed`/`skipped`); o Caso pode ficar `done` com falha parcial. Reprocessamento seletivo refaz só modalidades `failed` e refundição o Risco. Ciclo de vida: `pending`, `processing`, `done`, `failed`, `cancelled`, com retries e dead-letter.
_Avoid_: Job, request, upload, sessão, episódio contínuo

**Anomalia**:
Achado detectado em uma única modalidade (vídeo, áudio, vitais ou prescrições), com evidência e timestamp quando aplicável.
_Avoid_: Risco, alerta, erro, desvio (como sinônimo genérico)

**Análise Postural**:
Modalidade de vídeo baseada em MediaPipe Pose que mede ângulos e estabilidade para detectar desvios de movimento (foco: fisioterapia/reabilitação).
_Avoid_: OpenPose (usado só como referência conceitual), diagnóstico motor

**Detecção em Cena**:
Modalidade de vídeo baseada em YOLOv8 pré-treinado (COCO) que sinaliza presença/ausência de pessoas e objetos genéricos, aplicada de forma leve ao contexto cirúrgico via regras heurísticas — não é análise cirúrgica clínica.
_Avoid_: Detecção de sangramento, análise de procedimento cirúrgico, diagnóstico

**Série Vital**:
Sequência temporal sintética de sinais fisiológicos (ex.: frequência cardíaca, SpO2, pressão) associada a um Caso, com anomalias injetadas de forma controlada para demo e testes. Faixas calibradas por datasets públicos de referência (ex.: Kaggle/PhysioNet), sem PHI real em runtime.
_Avoid_: Prontuário real, streaming contínuo de monitor hospitalar

**Backend de Vitais**:
Modo do `VitalsAnomalyEngine` selecionado por `LIMEN_VITALS_BACKEND`: `thresholds` (limiares; default CI), `isolation_forest` (sklearn) ou `hybrid` (limiares OU IF). Autoencoder PyTorch é evidência de notebook — não é um valor deste backend.
_Avoid_: autoencoder no worker, Torch na imagem da API, download de dataset no runtime

**Prescrição**:
Registro de medicamento/dose/intervalo associado a um Caso. Anomalias vêm de regras determinísticas (faixa, intervalo, medicamento inesperado) e, quando houver histórico do Paciente, de desvio longitudinal vs. doses anteriores.
_Avoid_: Prescrição eletrônica hospitalar real, integração com farmácia

**Artefato**:
Arquivo binário de evidência ou resultado (vídeo, áudio, CSV, frame anotado) armazenado no object store; o Caso e o Postgres referenciam a chave, não o conteúdo.
_Avoid_: Blob genérico, attachment sem vínculo a Caso

**Provedor de Áudio**:
Origem efetiva da **fala** em um Caso: `azure`, `local` (fallback) ou `cache`. O badge `azure` significa que o Speech produziu a Transcrição — não que o Language também respondeu. Speech e Language degradam de forma independente: sem Speech não há Transcrição real; sem Language não há Sentimento, mas a Transcrição (e os Termos Críticos sobre ela) seguem. Um circuit breaker pode forçar `local` temporariamente após falhas consecutivas do Speech.
_Avoid_: “API de voz” genérica sem distinguir provedor, tratar Speech e Language como um único serviço, exigir Language para marcar `provider=azure`

**Transcrição**:
Texto em pt-BR produzido a partir do áudio de um Caso pelo Azure Speech. Só a Transcrição **real** (Speech) dispara Termo Crítico e alimenta Sentimento. O placeholder determinístico do fallback local (`local-transcript-{hash}`) **não** é Transcrição — não gera Termo Crítico nem Sentimento. A Transcrição real é armazenada como Artefato de texto no object store; é evidência da modalidade áudio, não uma modalidade nova.
_Avoid_: Legenda, log de fala, PHI em texto claro fora do object store, tratar placeholder local como Transcrição, transcrição como Caso ou modalidade separada

**Termo Crítico**:
Expressão clínica de risco (ex.: “falta de ar”) detectada na Transcrição real por lista determinística PT-BR (algoritmo sempre local) e opcionalmente corroborada por key phrases do Azure Language. Quando presente, gera uma Anomalia da modalidade áudio. Sem Transcrição real, não há Termo Crítico.
_Avoid_: Palavra-chave genérica, entidade médica sem risco, dependência exclusiva de Azure Language para detectar, Termo Crítico sobre placeholder local

**Sentimento**:
Polaridade afetiva da Transcrição estimada pelo Azure Text Analytics (Language). Sentimento fortemente negativo gera uma Anomalia da modalidade áudio; sem Azure fica indisponível e não bloqueia a fusão.
_Avoid_: Diagnóstico de humor, emoção como score clínico, Sentimento calculado sem Azure

**Risco**:
Resultado da fusão multimodal de um Caso: escore numérico e nível BAIXO, MEDIO ou ALTO, justificado pelas Anomalias e evidências das modalidades.
_Avoid_: Anomalia, score solto, probabilidade clínica real

**Justificativa**:
Explicação do Risco composta por contribuições por modalidade (pesos e riscos parciais, principais Anomalias) e uma narrativa curta gerada por template.
_Avoid_: Explicação por LLM, caixa-preta só com score

**Alerta**:
Notificação à equipe médica emitida somente após a fusão de um Caso, quando o Risco é MEDIO ou ALTO; inclui justificativas baseadas nas Anomalias do Caso. É versionado: reprocessamento que altera o limiar gera nova versão append-only do mesmo Alerta (histórico preservado); o feed SSE notifica atualização.
_Avoid_: Log, notificação genérica, e-mail obrigatório, alerta parcial por modalidade, sobrescrita silenciosa sem histórico

**Falha de Processamento**:
Caso cuja análise esgotou retries na fila e permanece em estado recuperável (inspecionar erro, redrive ou descartar), distinto de Alerta clínico.
_Avoid_: Alerta, DLQ como termo de produto, erro genérico de UI

**Operador**:
Membro autenticado da equipe que usa o sistema. Papéis: `medico` (Casos, Pacientes, Alertas, Rótulo Sensível) e `admin` (mesmo escopo + painel de Falhas de Processamento).
_Avoid_: User genérico sem papel, paciente como login

**Registro de Auditoria**:
Trilha imutável (append-only) de ações sensíveis do Operador, em especial desmascarar Rótulo Sensível e redrive/descarte de Falha de Processamento.
_Avoid_: Log de aplicação genérico, analytics

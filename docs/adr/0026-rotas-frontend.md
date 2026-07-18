# Rotas do frontend Limen

Mapa de rotas Next.js App Router: `/login` (pública); `/` dashboard; `/pacientes` e `/pacientes/[id]` (histórico + tendência); `/pacientes/[id]/novo-caso` (upload vinculado ao Paciente); `/casos/[id]` (detalhe multimodal + Justificativa); `/alertas` (SSE + versões); `/admin/falhas` (DLQ, papel admin). PT fixo sem i18n. Motivo: Paciente como âncora do Novo Caso reforça o domínio; DLQ isolada em `/admin`.

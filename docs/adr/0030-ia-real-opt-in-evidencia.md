# IA real opt-in com evidência commitada; CI/testes seguem sintético/stub

Para cobrir o que o edital grada (modelos reais + Azure Cognitive Services) sem
perder o maior trunfo do Limen — 256 testes de backend offline, rápidos e
determinísticos — as integrações de IA real (Azure Speech + Text Analytics,
YOLOv8 via `ultralytics`, Isolation Forest de vitais) ficam **opt-in por
variável de ambiente**. O runtime default do Compose, o CI e os testes
permanecem no caminho **sintético/stub** já existente.

A prova exigida pela banca **não** vem do CI: um script versionado
(`scripts/gerar-evidencia-real.sh`) liga os flags reais, roda as três frentes uma
vez e **commita os artefatos** em `data/evidencia/` (frames anotados,
transcrição + sentimento em JSON, notebook executado com os plots do Isolation
Forest). A evidência vive no repositório, reproduzível, independente de a demo
ao vivo dar certo.

## Flags de opt-in

- `AZURE_ENABLED=true` — habilita Speech + Text Analytics (ADR 0015 rege o
  circuit breaker; sem chave, degrada para `local`).
- `LIMEN_YOLO_BACKEND=ultralytics` / `LIMEN_POSE_BACKEND=mediapipe` — vídeo real
  (default `synthetic`; ADR 0007 rege o escopo).
- `LIMEN_VITALS_BACKEND=isolation_forest|hybrid` — vitais ML (default
  `thresholds`; ADR 0029 rege o desenho).

## Consequências

- O caminho real **não é exercitado pelo CI**, então pode apodrecer em silêncio.
  O guardrail aceito é a **execução de evidência versionada** (rodada e commitada
  antes da entrega), não um job de CI real.
- `worker-video` com `ultralytics` arrasta Torch e vira imagem pesada — aceitável
  porque é serviço separado da imagem da API (respeita o `avoid` de *Backend de
  Vitais* no `CONTEXT.md`: “Torch na imagem da API”).
- Contrato de saída das modalidades é **agnóstico de backend**: sintético e real
  produzem o mesmo formato (Anomalias + score), de modo que os testes sobre o
  sintético continuam válidos para o real.

## Alternativas rejeitadas

| Alternativa | Motivo |
| ----------- | ------ |
| Tornar o real o default do runtime/CI | Quebra os 256 testes offline; exige chave/GPU/rede para `git clone` rodar |
| Rodar os modelos reais no CI (self-hosted/GPU) | Custo e fragilidade desproporcionais para protótipo acadêmico |
| Demo ao vivo sem evidência commitada | Risco que derrubaria a prova se webcam/chave falhar no dia (erro observado em refs) |
| Não versionar modelos/artefatos de evidência | Clone “nu” não reproduz — erro observado em ref womens-safety |

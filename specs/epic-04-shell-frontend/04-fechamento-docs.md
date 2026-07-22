# Shell Frontend — Fechamento documental (T4.8)

## Objetivo

Fechar o Épico 4 com documentação operacional extensiva do frontend (guia de
uso com prints), troubleshooting para subir o Limen e script de automação da
stack completa.

## Status

**Concluída em 21 de julho de 2026** (T4.8).

## Escopo

- Guia de uso em `docs/frontend/guia-de-uso.md` com prints das rotas mínimas
- Troubleshooting em `docs/frontend/troubleshooting.md`
- Script `scripts/start-limen.sh` (up/smoke/down/reset)
- Script de captura `docs/frontend/scripts/capture-screenshots.mjs`
- Referências cruzadas no README principal e `docs/README.md`

Ficam fora: gate Lighthouse no CI; correção de persistência SQL do Caso no
worker (débito técnico do Épico 3/5); e2e Playwright em CI.

## Critérios de pronto

- [x] Guia + prints versionados
- [x] Troubleshooting
- [x] Script de start da aplicação
- [x] Índices atualizados

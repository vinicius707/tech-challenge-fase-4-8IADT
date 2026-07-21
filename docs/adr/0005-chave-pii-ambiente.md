# Criptografia do Rótulo Sensível via secret em ambiente

O Rótulo Sensível do Paciente é criptografado em repouso (Fernet) com chave em
`PII_ENCRYPTION_KEY` no ambiente (`.env` / secrets do Compose), nunca commitada
com valor de produção. Rotação manual documentada no README.

**Status (Épico 2):** implementado no CRUD/reveal de Paciente
(`specs/epic-02-identity/02-paciente-privacidade.md`). Create/update com rótulo
sem chave válida responde `503`; listagens e Pacientes sem rótulo não dependem
da chave.

Alternativas rejeitadas: Azure Key Vault neste momento (complexidade/custo fora
do F0); chave derivada da senha do Operador (inviável para equipe compartilhada
na demo).

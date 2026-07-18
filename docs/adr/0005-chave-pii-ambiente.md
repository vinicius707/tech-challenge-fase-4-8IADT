# Criptografia do Rótulo Sensível via secret em ambiente

O Rótulo Sensível do Paciente é criptografado em repouso (ex.: Fernet/AES) com chave em `PII_ENCRYPTION_KEY` no ambiente (`.env` / secrets do Compose), nunca commitada. Rotação manual documentada no README. Alternativas rejeitadas: Azure Key Vault neste momento (complexidade/custo fora do F0); chave derivada da senha do Operador (inviável para equipe compartilhada na demo).

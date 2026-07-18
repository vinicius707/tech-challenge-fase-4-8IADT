# Privacidade do Paciente: minimização + rótulo criptografado

Para alinhar o protótipo a princípios de LGPD/GDPR sem construir uma plataforma de compliance, o Paciente é identificado por código pseudônimo (`PAC-001`) e pode ter um Rótulo Sensível opcional criptografado em repouso e mascarado na UI. Não armazenamos CPF nem prontuário real; exclusão do Paciente remove Casos e artefatos associados. Alternativas rejeitadas: cadastro completo com PII em claro; fluxo formal de consentimento/retenção (fora do escopo do desafio).

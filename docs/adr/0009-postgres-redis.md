# Persistência: PostgreSQL + Redis

Estado de domínio (Pacientes, Casos, Anomalias, Risco, Alertas, Auditoria, metadados de Falha de Processamento) fica em PostgreSQL. Redis fica reservado à fila RQ (broker/resultados de job). Motivo: histórico por Paciente, auditoria e concorrência API/worker sem os limites do SQLite. Alternativa rejeitada: SQLite (frágil com worker paralelo); Redis como único store (ruim para modelo relacional e auditoria).

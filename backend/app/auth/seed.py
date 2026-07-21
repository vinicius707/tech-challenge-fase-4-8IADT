from __future__ import annotations

import os
import uuid

from app.auth.passwords import hash_password, verify_password
from app.auth.service import OperatorRecord, OperatorStore

_SEED_ROLES = (
    ("SEED_MEDICO_USERNAME", "SEED_MEDICO_PASSWORD", "medico"),
    ("SEED_ADMIN_USERNAME", "SEED_ADMIN_PASSWORD", "admin"),
)


def seed_operators(store: OperatorStore) -> None:
    """Cria ou atualiza os Operadores seed de forma idempotente.

    Papéis sem username/password no ambiente são ignorados, permitindo
    ambientes (ex.: CI) sem credenciais seed.
    """
    for username_var, password_var, role in _SEED_ROLES:
        username = os.getenv(username_var)
        password = os.getenv(password_var)
        if not username or not password:
            continue

        existing = store.get_by_username(username)
        if existing is not None and verify_password(password, existing.password_hash):
            continue

        store.save(
            OperatorRecord(
                id=existing.id if existing is not None else uuid.uuid4(),
                username=username,
                password_hash=hash_password(password),
                role=role,
            )
        )

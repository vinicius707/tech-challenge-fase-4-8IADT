from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


class PiiKeyUnavailableError(Exception):
    """Raised when PII_ENCRYPTION_KEY is missing or invalid for a label write."""


@dataclass(frozen=True)
class SensitiveLabelCipher:
    """Fernet wrapper for the Paciente Rótulo Sensível."""

    _fernet: Fernet | None

    @classmethod
    def from_environment(cls) -> SensitiveLabelCipher:
        raw = os.getenv("PII_ENCRYPTION_KEY")
        if not raw:
            return cls(_fernet=None)
        try:
            return cls(_fernet=Fernet(raw.encode("utf-8")))
        except (ValueError, TypeError):
            return cls(_fernet=None)

    @property
    def is_available(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if self._fernet is None:
            raise PiiKeyUnavailableError("PII_ENCRYPTION_KEY indisponível")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if self._fernet is None:
            raise PiiKeyUnavailableError("PII_ENCRYPTION_KEY indisponível")
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise PiiKeyUnavailableError("Falha ao descriptografar rótulo") from exc

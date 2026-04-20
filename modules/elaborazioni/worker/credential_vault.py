from __future__ import annotations

from cryptography.fernet import Fernet


class WorkerCredentialVault:
    def __init__(self, master_key: str) -> None:
        self._fernet = Fernet(master_key.encode("utf-8"))

    def decrypt(self, encrypted_password: bytes) -> str:
        return self._fernet.decrypt(encrypted_password).decode("utf-8")

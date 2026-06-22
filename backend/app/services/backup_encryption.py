from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"GAIAENC1"
CHUNK_SIZE = 1024 * 1024
SALT_SIZE = 16
NONCE_SIZE = 16
TAG_SIZE = 32
SCHEME = "aes-256-ctr+hmac-sha256"
KDF = "scrypt"
DEFAULT_PASSPHRASE_ENV_VAR = "ELABORAZIONI_DB_BACKUP_ENCRYPTION_PASSPHRASE"


class BackupEncryptionError(RuntimeError):
    """Raised when backup encryption or decryption cannot be completed safely."""


def encrypt_file(input_path: str | Path, output_path: str | Path, passphrase: str) -> dict[str, str]:
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    if not source.is_file():
        raise BackupEncryptionError(f"Backup source file not found: {source}")
    if not passphrase:
        raise BackupEncryptionError("Backup encryption passphrase is empty")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    encryption_key, mac_key = _derive_keys(passphrase, salt)
    encryptor = Cipher(algorithms.AES(encryption_key), modes.CTR(nonce)).encryptor()
    mac = hmac.new(mac_key, digestmod=hashlib.sha256)
    header = MAGIC + salt + nonce

    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, destination.open("wb") as dst:
        dst.write(header)
        mac.update(header)
        while True:
            chunk = src.read(CHUNK_SIZE)
            if not chunk:
                break
            encrypted_chunk = encryptor.update(chunk)
            if encrypted_chunk:
                dst.write(encrypted_chunk)
                mac.update(encrypted_chunk)
        tail = encryptor.finalize()
        if tail:
            dst.write(tail)
            mac.update(tail)
        dst.write(mac.digest())

    return {
        "scheme": SCHEME,
        "kdf": KDF,
        "passphrase_env_var": DEFAULT_PASSPHRASE_ENV_VAR,
    }


def decrypt_file(input_path: str | Path, output_path: str | Path, passphrase: str) -> None:
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    if not source.is_file():
        raise BackupEncryptionError(f"Encrypted backup file not found: {source}")
    if not passphrase:
        raise BackupEncryptionError("Backup decryption passphrase is empty")

    file_size = source.stat().st_size
    minimum_size = len(MAGIC) + SALT_SIZE + NONCE_SIZE + TAG_SIZE
    if file_size < minimum_size:
        raise BackupEncryptionError(f"Encrypted backup is too small or truncated: {source}")

    with source.open("rb") as src:
        header = src.read(len(MAGIC) + SALT_SIZE + NONCE_SIZE)
        magic = header[: len(MAGIC)]
        if magic != MAGIC:
            raise BackupEncryptionError(f"Encrypted backup has an invalid header: {source}")
        salt = header[len(MAGIC) : len(MAGIC) + SALT_SIZE]
        nonce = header[len(MAGIC) + SALT_SIZE :]
        encryption_key, mac_key = _derive_keys(passphrase, salt)
        decryptor = Cipher(algorithms.AES(encryption_key), modes.CTR(nonce)).decryptor()
        mac = hmac.new(mac_key, digestmod=hashlib.sha256)
        mac.update(header)
        ciphertext_size = file_size - len(header) - TAG_SIZE

        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("wb") as dst:
                remaining = ciphertext_size
                while remaining > 0:
                    chunk = src.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        raise BackupEncryptionError(f"Encrypted backup ended unexpectedly: {source}")
                    remaining -= len(chunk)
                    mac.update(chunk)
                    plaintext_chunk = decryptor.update(chunk)
                    if plaintext_chunk:
                        dst.write(plaintext_chunk)
                tail = decryptor.finalize()
                if tail:
                    dst.write(tail)
                expected_tag = src.read(TAG_SIZE)
            if not hmac.compare_digest(mac.digest(), expected_tag):
                raise BackupEncryptionError(f"Encrypted backup integrity check failed: {source}")
        except Exception:
            destination.unlink(missing_ok=True)
            raise


def strip_encrypted_suffix(filename: str) -> str:
    if filename.endswith(".enc"):
        return filename[:-4]
    return filename


def _derive_keys(passphrase: str, salt: bytes) -> tuple[bytes, bytes]:
    derived = hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return derived[:32], derived[32:]

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.backup_encryption import (
    BackupEncryptionError,
    decrypt_file,
    encrypt_file,
    strip_encrypted_suffix,
)


def test_encrypt_and_decrypt_file_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "gaia.dump"
    encrypted = tmp_path / "gaia.dump.enc"
    decrypted = tmp_path / "gaia-restored.dump"
    source.write_bytes(b"gaia-backup" * 1024)

    metadata = encrypt_file(source, encrypted, "super-secret-passphrase")
    decrypt_file(encrypted, decrypted, "super-secret-passphrase")

    assert metadata["scheme"]
    assert decrypted.read_bytes() == source.read_bytes()


def test_decrypt_file_rejects_tampered_ciphertext(tmp_path: Path) -> None:
    source = tmp_path / "gaia.dump"
    encrypted = tmp_path / "gaia.dump.enc"
    decrypted = tmp_path / "gaia-restored.dump"
    source.write_bytes(b"gaia-backup")

    encrypt_file(source, encrypted, "super-secret-passphrase")
    payload = bytearray(encrypted.read_bytes())
    payload[-1] ^= 0x01
    encrypted.write_bytes(payload)

    with pytest.raises(BackupEncryptionError):
        decrypt_file(encrypted, decrypted, "super-secret-passphrase")
    assert not decrypted.exists()


def test_strip_encrypted_suffix_handles_plain_and_encrypted_names() -> None:
    assert strip_encrypted_suffix("gaia.dump.enc") == "gaia.dump"
    assert strip_encrypted_suffix("gaia.dump") == "gaia.dump"

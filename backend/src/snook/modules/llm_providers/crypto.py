"""Cifra das chaves de LLM: AES-256-GCM com `SNOOK_MASTER_KEY` (ADR-0009, SEC-07)."""

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12


class MasterKeyMismatch(Exception):
    """Valor não decifra: chave-mestra trocada sem rotação ou linha adulterada."""

    def __init__(self) -> None:
        super().__init__("chave de LLM não decifra com a chave-mestra atual nem a anterior")


@dataclass(frozen=True)
class SealedKey:
    ciphertext: bytes  # inclui a tag do GCM
    nonce: bytes
    version: int


def decode_master_key(value: str) -> bytes:
    """Base64 url-safe, com ou sem `=`. Formato já validado pelo Settings."""
    raw = value.strip()
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def key_version(master_key: bytes) -> int:
    """Identificador de 1 byte da chave-mestra, gravado em `key_version`."""
    return hashlib.sha256(b"snook:master-key-id:" + master_key).digest()[0]


def _aad(user_id: str, provider: str) -> bytes:
    return f"snook:llm-key:v1:{user_id}:{provider}".encode()


class KeyCipher:
    """Cifra com a chave atual; decifra com a atual ou, durante a rotação, a anterior."""

    def __init__(self, current: bytes, previous: bytes | None = None) -> None:
        self._current = current
        self._keys = [current] if previous is None else [current, previous]
        self.version = key_version(current)

    def encrypt(self, plaintext: str, *, user_id: str, provider: str) -> SealedKey:
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = AESGCM(self._current).encrypt(
            nonce, plaintext.encode(), _aad(user_id, provider)
        )
        return SealedKey(ciphertext=ciphertext, nonce=nonce, version=self.version)

    def decrypt(self, sealed: SealedKey, *, user_id: str, provider: str) -> str:
        for key in self._keys:
            if key_version(key) != sealed.version:
                continue
            try:
                plaintext = AESGCM(key).decrypt(
                    sealed.nonce, sealed.ciphertext, _aad(user_id, provider)
                )
            except InvalidTag:
                continue
            return plaintext.decode()
        raise MasterKeyMismatch

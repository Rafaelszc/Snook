import base64

import pytest

from snook.modules.llm_providers.crypto import (
    KeyCipher,
    MasterKeyMismatch,
    decode_master_key,
)

KEY_A = bytes(range(32))
KEY_B = bytes(range(32, 64))
API_KEY = "sk-TesteChave-0123456789abcdef"  # nome libera no .gitleaks.toml


def test_roundtrip_returns_original_and_differs_from_it() -> None:
    """`llm-providers` 12, transversal 6."""
    cipher = KeyCipher(KEY_A)
    sealed = cipher.encrypt(API_KEY, user_id="u1", provider="openai")
    assert API_KEY.encode() not in sealed.ciphertext
    assert len(sealed.nonce) == 12
    assert cipher.decrypt(sealed, user_id="u1", provider="openai") == API_KEY


def test_nonce_is_fresh_per_encryption() -> None:
    cipher = KeyCipher(KEY_A)
    first = cipher.encrypt(API_KEY, user_id="u1", provider="openai")
    second = cipher.encrypt(API_KEY, user_id="u1", provider="openai")
    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


@pytest.mark.parametrize(("user_id", "provider"), [("u2", "openai"), ("u1", "anthropic")])
def test_value_copied_to_other_row_does_not_decrypt(user_id: str, provider: str) -> None:
    """SEC-07: AAD por Usuário e provedor."""
    cipher = KeyCipher(KEY_A)
    sealed = cipher.encrypt(API_KEY, user_id="u1", provider="openai")
    with pytest.raises(MasterKeyMismatch):
        cipher.decrypt(sealed, user_id=user_id, provider=provider)


def test_wrong_master_key_fails_typed_without_key_text() -> None:
    sealed = KeyCipher(KEY_A).encrypt(API_KEY, user_id="u1", provider="openai")
    with pytest.raises(MasterKeyMismatch) as info:
        KeyCipher(KEY_B).decrypt(sealed, user_id="u1", provider="openai")
    message = str(info.value)
    assert API_KEY not in message
    assert KEY_A.hex() not in message and KEY_B.hex() not in message


def test_previous_key_still_decrypts() -> None:
    """ADR-0009: a anterior só decifra, durante a rotação."""
    sealed = KeyCipher(KEY_A).encrypt(API_KEY, user_id="u1", provider="openai")
    cipher = KeyCipher(KEY_B, previous=KEY_A)
    assert cipher.decrypt(sealed, user_id="u1", provider="openai") == API_KEY
    resealed = cipher.encrypt(API_KEY, user_id="u1", provider="openai")
    assert resealed.version == cipher.version != sealed.version
    assert KeyCipher(KEY_B).decrypt(resealed, user_id="u1", provider="openai") == API_KEY


def test_decode_master_key_accepts_unpadded_urlsafe() -> None:
    encoded = base64.urlsafe_b64encode(KEY_A).decode().rstrip("=")
    assert decode_master_key(encoded) == KEY_A

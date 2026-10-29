import logging

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from tests.auth.helpers import PASSWORD, registration, user_count

_REGISTER = "/api/auth/register"


def test_valid_registration_returns_public_user(client: TestClient) -> None:
    """`auth` 1 e 11."""
    response = client.post(_REGISTER, json=registration())
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "username"}
    assert body["email"] == "ana@x.com"
    assert body["username"] == "ana"
    assert PASSWORD not in response.text
    assert "$2b$" not in response.text


def test_short_password_rejected(client: TestClient, settings: Settings) -> None:
    """`auth` 2."""
    response = client.post(_REGISTER, json=registration(password="1234567"))
    assert response.status_code == 422
    assert response.json()["error"]["fields"]["password"] == "senha com no mínimo 8 caracteres"
    assert user_count(settings.database_path) == 0


def test_taken_email_rejected(client: TestClient, settings: Settings) -> None:
    """`auth` 3."""
    client.post(_REGISTER, json=registration())
    response = client.post(_REGISTER, json=registration(username="outra"))
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "email_taken"
    assert "email" in error["message"]
    assert user_count(settings.database_path) == 1


def test_taken_username_rejected(client: TestClient, settings: Settings) -> None:
    """`auth` 4."""
    client.post(_REGISTER, json=registration())
    response = client.post(_REGISTER, json=registration(email="outra@x.com"))
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "username_taken"
    assert "nome de usuário" in error["message"]
    assert user_count(settings.database_path) == 1


@pytest.mark.parametrize(
    "email", ["ana", "ana@", "@x.com", "ana@x", "a na@x.com", "a" * 250 + "@x.com"]
)
def test_invalid_email_rejected(client: TestClient, settings: Settings, email: str) -> None:
    """`auth` 5."""
    response = client.post(_REGISTER, json=registration(email=email))
    assert response.status_code == 422
    assert "email" in response.json()["error"]["fields"]
    assert user_count(settings.database_path) == 0


def test_case_variant_collides(client: TestClient, settings: Settings) -> None:
    """`auth` 6."""
    client.post(_REGISTER, json=registration(email="Ana@x.com", username="Ana"))
    assert (
        client.post(_REGISTER, json=registration(email="ana@x.com", username="bob")).status_code
        == 409
    )
    assert (
        client.post(_REGISTER, json=registration(email="b@x.com", username="ana")).status_code
        == 409
    )
    assert user_count(settings.database_path) == 1


@pytest.mark.parametrize("username", ["ab", "a" * 31, "ana maria", "ana!", "anã"])
def test_invalid_username_rejected(client: TestClient, settings: Settings, username: str) -> None:
    """`auth` 7."""
    response = client.post(_REGISTER, json=registration(username=username))
    assert response.status_code == 422
    assert "username" in response.json()["error"]["fields"]
    assert user_count(settings.database_path) == 0


@pytest.mark.parametrize("username", ["abc", "a" * 30, "a_b.c-d", "Ana_2"])
def test_valid_username_accepted(client: TestClient, username: str) -> None:
    """`auth` 7, borda aceita."""
    assert client.post(_REGISTER, json=registration(username=username)).status_code == 201


def test_password_of_72_bytes_accepted(client: TestClient) -> None:
    """`auth` 28."""
    assert client.post(_REGISTER, json=registration(password="a" * 72)).status_code == 201


@pytest.mark.parametrize("password", ["a" * 73, "é" * 37])
def test_password_over_72_bytes_rejected(
    client: TestClient, settings: Settings, password: str
) -> None:
    """`auth` 28: conta bytes, não caracteres ("é" * 37 = 74 bytes)."""
    response = client.post(_REGISTER, json=registration(password=password))
    assert response.status_code == 422
    assert response.json()["error"]["fields"]["password"] == "senha com no máximo 72 bytes"
    assert user_count(settings.database_path) == 0


def test_extra_field_rejected(client: TestClient, settings: Settings) -> None:
    """SEC-09."""
    response = client.post(_REGISTER, json=registration(is_admin=True))
    assert response.status_code == 422
    assert "is_admin" in response.json()["error"]["fields"]
    assert user_count(settings.database_path) == 0


def test_register_without_origin_is_forbidden(client: TestClient, settings: Settings) -> None:
    """SEC-04."""
    response = client.post(
        _REGISTER, json=registration(), headers={"Origin": "http://evil.example"}
    )
    assert response.status_code == 403
    assert user_count(settings.database_path) == 0


def test_password_not_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """`auth` 10, logs (SEC-20), inclusive no cadastro recusado."""
    caplog.set_level(logging.DEBUG)
    client.post(_REGISTER, json=registration())
    client.post(_REGISTER, json=registration())
    client.post(_REGISTER, json=registration(password="é" * 37))
    assert PASSWORD not in caplog.text
    assert "é" * 37 not in caplog.text

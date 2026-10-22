import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from snook.core.clock import Clock, FakeClock, SystemClock
from snook.core.settings import Settings, SettingsError, load_settings
from tests.conftest import VALID_MASTER_KEY


def test_startup_fails_without_master_key() -> None:
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    assert "SNOOK_MASTER_KEY" in str(exc.value)


@pytest.mark.parametrize(
    "bad_value",
    [
        "segredo-curto-demais",
        "!!!não-é-base64!!!",
        base64.urlsafe_b64encode(bytes(16)).decode(),
        base64.urlsafe_b64encode(bytes(33)).decode(),
    ],
)
def test_invalid_master_key_fails_without_echoing_value(
    monkeypatch: pytest.MonkeyPatch, bad_value: str
) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", bad_value)
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    text = str(exc.value)
    assert "SNOOK_MASTER_KEY" in text
    assert bad_value not in text
    assert bad_value not in repr(exc.value)


def test_invalid_previous_master_key_fails_without_echoing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_MASTER_KEY_PREVIOUS", "anterior-invalida")
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    assert "anterior-invalida" not in str(exc.value)


def test_master_key_is_not_leaked_by_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    settings = load_settings(env_file=None)
    assert VALID_MASTER_KEY not in repr(settings)
    assert VALID_MASTER_KEY not in str(settings)
    assert settings.snook_master_key.get_secret_value() == VALID_MASTER_KEY


def test_defaults_follow_deployment_spec(settings: Settings) -> None:
    assert settings.snook_master_key_previous is None
    assert settings.hf_token is None
    assert settings.session_cookie_secure == "auto"
    assert settings.session_idle_seconds == 86400
    assert settings.session_max_seconds == 604800
    assert settings.bcrypt_rounds == 12
    assert settings.login_max_failures == 5
    assert settings.login_max_failures_per_ip == 20
    assert settings.login_window_seconds == 900
    assert settings.llm_test_max_calls == 10
    assert settings.llm_test_window_seconds == 600
    assert settings.transcription_max_per_user == 1
    assert settings.transcription_workers == 2
    assert settings.generation_workers == 2
    assert settings.trusted_proxy_ips == ["172.28.0.10", "172.28.0.11"]
    assert settings.upload_max_bytes == 524288000
    assert settings.max_audio_seconds == 7200
    assert settings.llm_read_timeout == 300
    assert settings.whisper_model == "large-v3-turbo"
    assert settings.whisper_compute_type == "int8"
    assert settings.pyannote_pipeline == "pyannote/speaker-diarization-3.1"
    assert settings.models_offline is False
    assert settings.log_level == "INFO"
    assert settings.database_path == Path("/data/snook.db")
    assert settings.audio_root == Path("/audios")
    assert settings.models_root == Path("/models")
    assert settings.allowed_hosts == ["localhost", "127.0.0.1"]
    assert settings.allowed_origins == ["http://localhost:8080", "http://127.0.0.1:8080"]


def test_bcrypt_rounds_come_from_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")
    assert load_settings(env_file=None).bcrypt_rounds == 4


def test_lan_host_extends_allowed_hosts_and_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.casa.lan")
    s = load_settings(env_file=None)
    assert s.allowed_hosts == ["localhost", "127.0.0.1", "snook.casa.lan"]
    assert s.allowed_origins == [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://snook.casa.lan",
    ]


def test_lan_host_accepts_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "192.168.0.10")
    assert "192.168.0.10" in load_settings(env_file=None).allowed_hosts


def test_explicit_allowed_lists_replace_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.casa.lan")
    monkeypatch.setenv("ALLOWED_HOSTS", "a.example, b.example")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example")
    s = load_settings(env_file=None)
    assert s.allowed_hosts == ["a.example", "b.example"]
    assert s.allowed_origins == ["https://a.example"]


@pytest.mark.parametrize(
    "bad_host",
    [
        "https://snook.lan",
        "snook.lan:8443",
        "snook.lan/path",
        "snook lan",
        "-snook.lan",
        "snook..lan",
        "999.1.1.1.1",
    ],
)
def test_invalid_lan_host_blocks_startup(monkeypatch: pytest.MonkeyPatch, bad_host: str) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", bad_host)
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    assert "SNOOK_LAN_HOST" in str(exc.value)


def test_empty_lan_host_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "")
    assert load_settings(env_file=None).allowed_hosts == ["localhost", "127.0.0.1"]


def test_trusted_proxy_ips_must_be_ips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "172.28.0.10,nginx")
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    assert "TRUSTED_PROXY_IPS" in str(exc.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BCRYPT_ROUNDS", "3"),
        ("UPLOAD_MAX_BYTES", "0"),
        ("TRANSCRIPTION_WORKERS", "0"),
        ("SESSION_COOKIE_SECURE", "talvez"),
        ("LOG_LEVEL", "VERBOSE"),
    ],
)
def test_out_of_range_values_block_startup(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv(name, value)
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    assert name in str(exc.value)


def test_clock_can_be_replaced_by_a_fake() -> None:
    def stamp(clock: Clock) -> datetime:
        return clock.now()

    start = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    fake = FakeClock(start)
    assert stamp(fake) == start
    fake.advance(timedelta(minutes=5))
    assert stamp(fake) == start + timedelta(minutes=5)


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_fake_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone"):
        FakeClock(datetime(2026, 10, 22, 12, 0))

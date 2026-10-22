import base64
import binascii
import ipaddress
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DNS_LABEL = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_MASTER_KEY_BYTES = 32
_LOCAL_HOSTS = ["localhost", "127.0.0.1"]
_LOCAL_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]

CommaList = Annotated[list[str], NoDecode]


class SettingsError(Exception):
    """Configuração inválida. A mensagem lista variáveis e motivos, nunca valores."""


def _decode_master_key(value: SecretStr) -> SecretStr:
    raw = value.get_secret_value().strip()
    padded = raw + "=" * (-len(raw) % 4)
    try:
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("deve ser base64 url-safe de 32 bytes") from None
    if len(decoded) != _MASTER_KEY_BYTES:
        raise ValueError("deve ser base64 url-safe de 32 bytes")
    return SecretStr(raw)


def _is_valid_lan_host(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        return True
    if len(value) > 253:
        return False
    labels = value.split(".")
    if not all(_DNS_LABEL.match(label) for label in labels):
        return False
    # "999.1.1.1.1" parece IP e não é: nome todo numérico não vale como DNS.
    return not labels[-1].isdigit()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    snook_master_key: SecretStr
    snook_master_key_previous: SecretStr | None = None
    hf_token: SecretStr | None = None

    snook_lan_host: str | None = None
    allowed_hosts: CommaList = Field(default_factory=lambda: list(_LOCAL_HOSTS))
    allowed_origins: CommaList = Field(default_factory=lambda: list(_LOCAL_ORIGINS))
    trusted_proxy_ips: CommaList = Field(default_factory=lambda: ["172.28.0.10", "172.28.0.11"])

    session_cookie_secure: Literal["auto", "true", "false"] = "auto"
    session_idle_seconds: int = Field(86400, ge=1)
    session_max_seconds: int = Field(604800, ge=1)
    bcrypt_rounds: int = Field(12, ge=4, le=31)

    login_max_failures: int = Field(5, ge=1)
    login_max_failures_per_ip: int = Field(20, ge=1)
    login_window_seconds: int = Field(900, ge=1)
    llm_test_max_calls: int = Field(10, ge=1)
    llm_test_window_seconds: int = Field(600, ge=1)
    transcription_max_per_user: int = Field(1, ge=1)
    transcription_workers: int = Field(2, ge=1)
    generation_workers: int = Field(2, ge=1)

    upload_max_bytes: int = Field(524288000, ge=1)
    max_audio_seconds: int = Field(7200, ge=1)
    llm_read_timeout: int = Field(300, ge=1)

    whisper_model: str = "large-v3-turbo"
    whisper_compute_type: str = "int8"
    whisper_revision: str = ""
    pyannote_pipeline: str = "pyannote/speaker-diarization-3.1"
    pyannote_revision: str = ""
    models_offline: bool = False

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_path: Path = Path("/data/snook.db")
    audio_root: Path = Path("/audios")
    models_root: Path = Path("/models")

    @field_validator("snook_master_key", "snook_master_key_previous")
    @classmethod
    def _check_master_key(cls, value: SecretStr | None) -> SecretStr | None:
        return None if value is None else _decode_master_key(value)

    @field_validator("allowed_hosts", "allowed_origins", "trusted_proxy_ips", mode="before")
    @classmethod
    def _split_commas(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("trusted_proxy_ips")
    @classmethod
    def _check_proxy_ips(cls, value: list[str]) -> list[str]:
        for item in value:
            try:
                ipaddress.ip_address(item)
            except ValueError:
                raise ValueError("deve ser lista de IPs separados por vírgula") from None
        return value

    @field_validator("snook_lan_host")
    @classmethod
    def _check_lan_host(cls, value: str | None) -> str | None:
        if value is not None and not _is_valid_lan_host(value):
            raise ValueError("deve ser nome DNS ou IP, sem esquema, porta ou caminho")
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_log_level(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _derive_lan_lists(self) -> "Settings":
        if self.snook_lan_host is None:
            return self
        if "allowed_hosts" not in self.model_fields_set:
            self.allowed_hosts = [*_LOCAL_HOSTS, self.snook_lan_host]
        if "allowed_origins" not in self.model_fields_set:
            self.allowed_origins = [*_LOCAL_ORIGINS, f"https://{self.snook_lan_host}"]
        return self


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        problems = [
            f"{str(err['loc'][0]).upper()}: {err['msg']}" if err["loc"] else err["msg"]
            for err in exc.errors(include_input=False, include_url=False)
        ]
        raise SettingsError("configuração inválida: " + "; ".join(problems)) from None

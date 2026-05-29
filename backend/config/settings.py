from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULTS = {
    "changeme-in-production-use-long-random-string",
    "dev-secret-key-change-in-production-at-least-32-chars",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_version: str = "0.1.0"
    app_name: str = "Karpathys"
    secret_key: str = "changeme-in-production-use-long-random-string"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/karpathys"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = ["http://localhost:3000"]

    jwt_algorithm: str = "HS256"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v

    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 7

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_secure(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_secret_key_insecure(self) -> bool:
        return self.secret_key in _INSECURE_DEFAULTS


settings = Settings()

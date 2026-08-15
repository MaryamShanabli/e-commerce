from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_FALLBACK_SECRET = "dev-only-secret-key-not-for-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./dev.db"
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:3000"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._resolve_secret()

    def _resolve_secret(self) -> None:
        if self.JWT_SECRET_KEY:
            return
        if self.DATABASE_URL.startswith("sqlite"):
            self.JWT_SECRET_KEY = _DEV_FALLBACK_SECRET
            return
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or empty. Set it in the environment "
            "(or .env) before starting the application."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

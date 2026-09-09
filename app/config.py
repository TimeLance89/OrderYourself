"""Konfiguration ohne Händler-, Liefer- oder Bestellanbieter-Abhängigkeit."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore", env_ignore_empty=True)
    database_path: str = "data/order_yourself.db"
    web_csrf_secret: str = ""
    trusted_proxy_header: str = ""
    trusted_proxy_value: str = ""

    @property
    def database_url(self) -> str:
        path = Path(self.database_path)
        if not path.is_absolute(): path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"


settings = Settings()

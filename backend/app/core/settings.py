from pathlib import Path

from pydantic_settings import DotEnvSettingsSource
from pydantic_settings import EnvSettingsSource
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "app.db"


class Settings(BaseSettings):
    app_name: str = "kg-mvp"
    app_env: str = "dev"
    debug: bool = True

    sqlite_url: str = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "xpsdd520"

    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings: EnvSettingsSource,
        dotenv_settings: DotEnvSettingsSource,
        file_secret_settings,
    ):
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

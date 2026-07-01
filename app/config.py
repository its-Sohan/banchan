"""App configuration loaded from environment / .env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://banchan:banchan@localhost:5432/banchan"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    upload_dir: str = "./uploads"
    max_image_bytes: int = 10 * 1024 * 1024

    site_name: str = "Banchan"
    secret_key: str = "dev-only-change-me"

    seed_boards: str = "b,g,tech"

    # Derived
    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        return p if p.is_absolute() else self.project_root / p

    @property
    def originals_path(self) -> Path:
        return self.upload_path / "originals"

    @property
    def thumbs_path(self) -> Path:
        return self.upload_path / "thumbs"

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).resolve().parent / "templates"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parent / "static"


settings = Settings()

# Ensure upload dirs exist
settings.originals_path.mkdir(parents=True, exist_ok=True)
settings.thumbs_path.mkdir(parents=True, exist_ok=True)

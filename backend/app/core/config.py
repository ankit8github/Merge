from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MERGE_", env_file=BACKEND_ROOT / ".env", extra="ignore"
    )

    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "merge_dev"
    db_user: str = "merge_app"
    db_password: SecretStr = SecretStr("")

    def database_url(self) -> URL:
        # Phase 0 guard: migration and smoke commands cannot target another DB/role.
        if (
            self.db_host != "127.0.0.1"
            or self.db_port != 5432
            or self.db_name != "merge_dev"
            or self.db_user != "merge_app"
        ):
            raise ValueError("Phase 0 requires local merge_dev with the merge_app role")
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value() or None,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

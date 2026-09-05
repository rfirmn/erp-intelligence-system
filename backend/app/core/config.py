from typing import List, Optional, Union
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Settings
    PROJECT_NAME: str = "ERP Intelligence Dashboard API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_STR: str = "/api/v1"

    # Security & Auth
    SECRET_KEY: str = "dev-insecure-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SECURITY_ENABLED: bool = False

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # PostgreSQL Feature Store Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: str = "rio"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "erp_intelligence_fs"

    # Connection Pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT_SECONDS: int = 10

    # ERP Source Connection & Ingestion
    ERP_DATABASE_URL: Optional[str] = None
    ERP_MOCK_DATA: bool = True
    ALLOW_MOCK_IN_PRODUCTION: bool = False
    INGESTION_BATCH_SIZE: int = 5000
    SCHEDULER_ENABLED: bool = True

    def get_database_url(self) -> str:
        """Dynamically assemble the asyncpg PostgreSQL connection URL if not directly specified."""
        if self.DATABASE_URL:
            # Ensure it uses the asyncpg driver
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        auth = self.POSTGRES_USER
        if self.POSTGRES_PASSWORD:
            auth += f":{self.POSTGRES_PASSWORD}"

        return (
            f"postgresql+asyncpg://{auth}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def is_mock_source(self) -> bool:
        """Determine whether the system should run against the mock generator or live ERP database."""
        if self.ENVIRONMENT == "production":
            if self.ERP_MOCK_DATA and not self.ALLOW_MOCK_IN_PRODUCTION:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: ERP_MOCK_DATA cannot be True in 'production' environment "
                    "without explicit ALLOW_MOCK_IN_PRODUCTION=True override."
                )
            return False if self.ERP_DATABASE_URL else False
        return self.ERP_MOCK_DATA or (self.ERP_DATABASE_URL is None)


settings = Settings()


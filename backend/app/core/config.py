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

    # 1. Application Settings
    PROJECT_NAME: str = "ERP Intelligence Dashboard API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_STR: str = "/api/v1"

    # 2. Security & Auth (Strict: Wajib disuplai dari .env / Environment)
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SECURITY_ENABLED: bool = False
    DEV_USER_ID: str = "usr-001"
    DEV_USER_USERNAME: str = "admin@isp.net"
    DEV_USER_PASSWORD: str
    DEV_USER_FULL_NAME: str = "System Administrator"
    DEV_USER_ROLE: str = "admin"

    # 3. CORS
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

    # 4. PostgreSQL Feature Store Database (Strict: Kredensial wajib dari .env)
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    # Connection Pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT_SECONDS: int = 10

    # 5. ERP Source Connection & Ingestion (Strict: Kredensial wajib dari .env)
    ERP_DATABASE_URL: Optional[str] = None
    ERP_DB_USER: str
    ERP_DB_PASSWORD: str
    ERP_DB_HOST: str = "localhost"
    ERP_DB_PORT: int = 5433
    ERP_DB_NAME: str
    ERP_DB_POOL_SIZE: int = 3
    ERP_MOCK_DATA: bool = True
    ALLOW_MOCK_IN_PRODUCTION: bool = False
    INGESTION_BATCH_SIZE: int = 5000
    SCHEDULER_ENABLED: bool = True

    # 6. AI & LLM Engine Configuration (Zone 3 & 4)
    LLM_PROVIDER: str = "gemini"  # "gemini" | "openai" | "fallback"
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT_SECONDS: float = 15.0
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # 7. Agent & Safety Configuration (Zone 3)
    AGENT_SQL_MAX_ROWS: int = 100
    AGENT_HIGH_RISK_LIMIT: int = 25

    def get_database_url(self) -> str:
        """Dynamically assemble the asyncpg PostgreSQL connection URL if not directly specified."""
        if self.DATABASE_URL:
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

    def get_erp_database_url(self) -> str:
        """Assemble asyncpg PostgreSQL connection URL for ERP source."""
        if self.ERP_DATABASE_URL:
            url = self.ERP_DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        auth = self.ERP_DB_USER
        if self.ERP_DB_PASSWORD:
            auth += f":{self.ERP_DB_PASSWORD}"

        return (
            f"postgresql+asyncpg://{auth}@{self.ERP_DB_HOST}:{self.ERP_DB_PORT}/{self.ERP_DB_NAME}"
        )

    def is_mock_source(self) -> bool:
        """Determine whether the system should run against the mock generator or live ERP database."""
        if self.ENVIRONMENT == "production":
            if self.ERP_MOCK_DATA and not self.ALLOW_MOCK_IN_PRODUCTION:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: ERP_MOCK_DATA cannot be True in 'production' environment "
                    "without explicit ALLOW_MOCK_IN_PRODUCTION=True override."
                )
            return False if (self.ERP_DATABASE_URL or self.ERP_DB_HOST) else False
        return self.ERP_MOCK_DATA or (self.ERP_DATABASE_URL is None and not self.ERP_DB_HOST)


settings = Settings()  # type: ignore

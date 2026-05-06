from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application Settings
    app_name: str = "LeoPals"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # LLM Settings
    openai_api_key: str
    openai_api_base: str = "https://api.deepseek.com/v1"
    llm_model_name: str = "deepseek-chat"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # Embedding Settings
    embedding_model_name: str = "nomic-embed-text:v1.5"
    embedding_dimension: int = 768

    # Ollama Settings
    ollama_host: str = "http://localhost:11434"

    # PostgreSQL (pgvector) Settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: Optional[str] = None
    postgres_db: str = "leopals"

    # Redis Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def postgres_dsn(self) -> str:
        password_part = f":{self.postgres_password}" if self.postgres_password else ""
        return f"postgresql://{self.postgres_user}{password_part}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_url(self) -> str:
        password_part = f":{self.postgres_password}" if self.postgres_password else ""
        return f"postgresql+asyncpg://{self.postgres_user}{password_part}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
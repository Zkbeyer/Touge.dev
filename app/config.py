from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mountain_pass_streak"
    sync_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/mountain_pass_streak"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "changeme-dev-secret"
    token_encryption_key: str = ""  # Fernet key, base64 encoded

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    lc_api_base_url: str = "https://alfa-leetcode-api.onrender.com"

    app_base_url: str = "http://localhost:8000"
    environment: str = "development"
    debug: bool = True

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days


settings = Settings()

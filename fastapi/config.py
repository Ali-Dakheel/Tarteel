from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    INTERNAL_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    ENVIRONMENT: str = "local"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

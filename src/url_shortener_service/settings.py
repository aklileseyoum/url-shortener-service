from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    model_config = SettingsConfigDict(env_file=".env")

    postgres_host: str = "localhost"
    postgres_port: str = "5433"
    postgres_user: str
    postgres_password: str
    postgres_db: str


settings = Settings()  # type: ignore[call-arg]

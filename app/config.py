from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou do arquivo .env em desenvolvimento)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_senha: str = ""
    session_secret: str = "dev-inseguro"
    database_url: str = "sqlite:///./biju.db"
    anthropic_api_key: str = ""


settings = Settings()

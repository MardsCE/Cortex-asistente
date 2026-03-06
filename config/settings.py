import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuracion centralizada desde variables de entorno."""

    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/cortex.db")


settings = Settings()

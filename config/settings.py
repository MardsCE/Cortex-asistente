import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuración centralizada desde variables de entorno."""

    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_PREFIX: str = os.getenv("DISCORD_PREFIX", "!")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cortex.db")


settings = Settings()

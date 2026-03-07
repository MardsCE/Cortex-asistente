import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuracion centralizada desde variables de entorno."""

    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-3.1-flash-lite-preview")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Mexico_City")
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json"
    )
    ALLOWED_USERS: list[str] = [
        u.strip() for u in os.getenv("ALLOWED_USERS", "").split(",") if u.strip()
    ]


settings = Settings()

if not settings.TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN no configurado. Revisa tu archivo .env")
if not settings.OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY no configurado. Revisa tu archivo .env")

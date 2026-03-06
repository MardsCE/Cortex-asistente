from datetime import datetime
from zoneinfo import ZoneInfo
from config.settings import settings


def ahora() -> datetime:
    """Devuelve la hora actual en la zona horaria configurada (Mexico por defecto)."""
    return datetime.now(ZoneInfo(settings.TIMEZONE))

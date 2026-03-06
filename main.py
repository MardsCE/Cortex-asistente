import threading
import uvicorn
from config.settings import settings


def start_api():
    """Lanza la API FastAPI en un hilo daemon."""
    from api.main import app

    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)


def main():
    # Lanzar API en hilo daemon
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    print(f"[Cortex] API iniciada en http://{settings.API_HOST}:{settings.API_PORT}")

    # Lanzar bot de Discord en el hilo principal (bloqueante)
    from bot.syn import run_bot

    print("[Cortex] Iniciando bot Syn...")
    run_bot()


if __name__ == "__main__":
    main()

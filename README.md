# Cortex-asistente

Plataforma de asistencia operativa con IA. Bot de Discord llamado **Syn** que responde usando OpenRouter API, y una API REST con FastAPI.

## Stack

- Python 3.11+
- FastAPI + Uvicorn (backend / API REST)
- discord.py (bot de Discord "Syn")
- OpenRouter API (IA, modelo `anthropic/claude-sonnet-4-20250514`)
- SQLite + SQLAlchemy (preparado para futuro)
- python-dotenv para variables de entorno

## Estructura

```
Cortex-asistente/
├── main.py                        # Punto de entrada - lanza API y Bot en paralelo
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── api/
│   ├── __init__.py
│   └── main.py                    # FastAPI con endpoints REST
├── bot/
│   ├── __init__.py
│   └── syn.py                     # Bot de Discord (Syn)
├── config/
│   ├── __init__.py
│   └── settings.py                # Config centralizada desde .env
├── services/
│   ├── __init__.py
│   └── openrouter_service.py      # Integración con OpenRouter API
├── core/
│   └── __init__.py
├── models/
│   └── __init__.py
└── utils/
    └── __init__.py
```

## Instalacion

```bash
# Clonar el repositorio
git clone https://github.com/MardsCE/Cortex-asistente.git
cd Cortex-asistente

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus tokens y configuracion
```

## Configuracion

Copia `.env.example` a `.env` y completa las variables:

| Variable | Descripcion | Default |
|---|---|---|
| `DISCORD_TOKEN` | Token del bot de Discord | - |
| `DISCORD_PREFIX` | Prefijo de comandos | `!` |
| `OPENROUTER_API_KEY` | API key de OpenRouter | - |
| `OPENROUTER_MODEL` | Modelo de IA a usar | `anthropic/claude-sonnet-4-20250514` |
| `API_HOST` | Host de la API | `0.0.0.0` |
| `API_PORT` | Puerto de la API | `8000` |
| `DATABASE_URL` | URL de la base de datos | `sqlite:///./cortex.db` |

## Uso

```bash
python main.py
```

Esto lanza simultaneamente:
- **API REST** en `http://0.0.0.0:8000`
- **Bot Syn** en Discord

## Comandos de Discord

| Comando | Descripcion |
|---|---|
| `!syn <mensaje>` | Habla con Syn, el asistente de Cortex |
| `!status` | Muestra el estado del sistema |
| `!ping` | Verifica la latencia del bot |

## Endpoints API

| Metodo | Ruta | Descripcion |
|---|---|---|
| `GET` | `/` | Info del sistema |
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Chat con Syn (body: `{"message": "...", "user_id": "..."}`) |

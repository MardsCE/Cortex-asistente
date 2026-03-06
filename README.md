# Cortex-asistente

Plataforma de asistencia operativa con IA. Bot de Telegram llamado **Syn** que responde usando OpenRouter API, y una API REST con FastAPI. Preparado para correr en Docker con multiples instancias.

## Stack

- Python 3.11+
- FastAPI + Uvicorn (API REST)
- python-telegram-bot (bot de Telegram "Syn")
- OpenRouter API (IA, modelo `anthropic/claude-sonnet-4-20250514`)
- SQLite + SQLAlchemy (preparado para futuro)
- Docker + Docker Compose (despliegue multi-instancia)

## Estructura

```
Cortex-asistente/
├── main.py                        # Punto de entrada - API y Bot en paralelo
├── Dockerfile
├── docker-compose.yml
├── install.sh                     # Instalacion rapida en VPS
├── add-instance.sh                # Agregar nuevas instancias
├── requirements.txt
├── .env.example
├── api/
│   └── main.py                    # FastAPI con endpoints REST
├── bot/
│   └── syn.py                     # Bot de Telegram (Syn)
├── config/
│   └── settings.py                # Config centralizada desde .env
├── services/
│   └── openrouter_service.py      # Integracion con OpenRouter API
├── core/
├── models/
└── utils/
```

## Instalacion rapida en VPS

```bash
git clone https://github.com/MardsCE/Cortex-asistente.git
cd Cortex-asistente
bash install.sh
```

El script instala Docker si no existe, crea `.env` desde el template y muestra los comandos disponibles.

### Configurar tokens

```bash
nano .env
```

| Variable | Descripcion | Default |
|---|---|---|
| `TELEGRAM_TOKEN` | Token del bot de Telegram (@BotFather) | - |
| `OPENROUTER_API_KEY` | API key de OpenRouter | - |
| `OPENROUTER_MODEL` | Modelo de IA | `anthropic/claude-sonnet-4-20250514` |
| `API_HOST` | Host de la API | `0.0.0.0` |
| `API_PORT` | Puerto de la API | `8000` |
| `DATABASE_URL` | URL de la base de datos | `sqlite:///./data/cortex.db` |

### Iniciar

```bash
docker compose up -d --build
```

### Ver logs

```bash
docker compose logs -f
```

## Multiples instancias

Cada instancia corre en su propio contenedor con su bot de Telegram, datos y puerto independientes:

```bash
# Agregar una segunda instancia en puerto 8002
bash add-instance.sh cortex-2 8002

# Editar tokens de la nueva instancia
nano .env.cortex-2

# Levantar solo esa instancia
docker compose up -d --build cortex-2
```

Cada instancia tiene su propio volumen Docker para datos persistentes (DB, archivos).

## Comandos de Telegram

| Comando | Descripcion |
|---|---|
| `/inicio` | Mensaje de bienvenida |
| `/estado` | Estado del sistema |
| `/limpiar` | Limpiar historial |
| `/ayuda` | Ver comandos |
| _(cualquier texto)_ | Hablar con Syn directamente |

## Endpoints API

| Metodo | Ruta | Descripcion |
|---|---|---|
| `GET` | `/` | Info del sistema |
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Chat con Syn (`{"message": "...", "user_id": "..."}`) |

## Comandos Docker

```bash
docker compose up -d --build    # Iniciar
docker compose down              # Detener
docker compose restart           # Reiniciar
docker compose logs -f           # Ver logs
```

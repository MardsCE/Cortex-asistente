# Cortex-asistente (Syn) - Guia de Instalacion

## Requisitos del servidor

- Linux (Ubuntu 20.04+ recomendado) o cualquier SO con Docker
- Docker y Docker Compose
- 1 GB RAM minimo
- Acceso a internet (para Telegram, OpenRouter y Google Drive API)

---

## 1. Prerequisitos externos (hacer ANTES de instalar)

### 1.1 Bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Envia `/newbot`, sigue las instrucciones
3. Copia el **token** que te da (formato: `123456789:ABCdefGHI...`)

### 1.2 API de OpenRouter

1. Crea cuenta en [openrouter.ai](https://openrouter.ai)
2. Ve a **Keys** y genera una API key
3. Copia la key (formato: `sk-or-v1-...`)

### 1.3 Google Cloud - Service Account (para leer archivos de Drive)

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un proyecto nuevo (o usa uno existente)
3. **Habilitar API**:
   - Ve a **APIs y servicios** > **Habilitar APIs y servicios**
   - Busca **"Google Drive API"** > clic en **Habilitar**
4. **Crear Service Account**:
   - Ve a **IAM y administracion** > **Cuentas de servicio**
   - Clic en **+ Crear cuenta de servicio**
   - Nombre: `syn-drive-bot` (o el que quieras)
   - Clic en **Crear y continuar** > **Continuar** > **Listo**
5. **Generar clave JSON**:
   - Clic en la cuenta creada > pestana **Claves**
   - **Agregar clave** > **Crear clave nueva** > **JSON** > **Crear**
   - Se descarga un archivo `.json` — guardalo, lo necesitaras

> **Email del service account**: lo encuentras en la consola (formato: `nombre@proyecto.iam.gserviceaccount.com`). Los usuarios deben compartir sus archivos de Drive con este email para que el bot pueda leerlos.

---

## 2. Instalacion

### 2.1 Clonar el repositorio

```bash
git clone https://github.com/MardsCE/Cortex-asistente.git
cd Cortex-asistente
```

### 2.2 Ejecutar instalador

```bash
bash install.sh
```

Esto instala Docker si no esta presente y crea el archivo `.env`.

### 2.3 Configurar variables de entorno

Edita el archivo `.env`:

```bash
nano .env
```

Contenido:

```env
TELEGRAM_TOKEN=tu_token_de_telegram
OPENROUTER_API_KEY=tu_api_key_de_openrouter
OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview
API_HOST=0.0.0.0
API_PORT=8000
TIMEZONE=America/Mexico_City
ALLOWED_USERS=id_telegram_usuario1,id_telegram_usuario2
GOOGLE_SERVICE_ACCOUNT_FILE=credentials/service_account.json
```

**Variables importantes:**

| Variable | Descripcion |
|---|---|
| `TELEGRAM_TOKEN` | Token del bot de BotFather |
| `OPENROUTER_API_KEY` | API key de OpenRouter |
| `OPENROUTER_MODEL` | Modelo de IA a usar (ver [modelos disponibles](https://openrouter.ai/models)) |
| `TIMEZONE` | Zona horaria para recordatorios |
| `ALLOWED_USERS` | IDs de Telegram separados por coma. Dejar vacio = todos pueden usar el bot |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Ruta al JSON del service account |

> **Como obtener tu ID de Telegram**: Habla con [@userinfobot](https://t.me/userinfobot) y te dice tu ID.

### 2.4 Colocar credenciales de Google

Crea la carpeta y copia el archivo JSON que descargaste en el paso 1.3:

```bash
mkdir -p credentials
cp /ruta/al/archivo-descargado.json credentials/service_account.json
```

### 2.5 Instalar LibreOffice (para capturas de Excel)

El bot genera capturas de pantalla reales de archivos. Para archivos Excel (XLSX), necesita LibreOffice.

**Opcion A: Ya incluido en Docker** (si usas Docker, no necesitas hacer nada extra — ya esta en el Dockerfile).

**Opcion B: Instalacion local** (si corres sin Docker):

```bash
# Ubuntu/Debian
sudo apt-get install -y libreoffice-calc

# Solo necesitas el componente calc, no la suite completa
```

---

## 3. Iniciar el bot

### Con Docker (recomendado)

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker compose logs -f
```

Detener:

```bash
docker compose down
```

Reiniciar:

```bash
docker compose restart
```

### Sin Docker (desarrollo/pruebas)

```bash
pip install -r requirements.txt
python main.py
```

---

## 4. Multiples instancias

Puedes correr varios bots independientes (cada uno con su token de Telegram):

```bash
# Crear nueva instancia
bash add-instance.sh cortex-2 8002

# Editar su configuracion
nano .env.cortex-2

# Levantar
docker compose up -d --build cortex-2
```

Listar instancias:

```bash
bash list-instances.sh
```

Eliminar instancia:

```bash
bash remove-instance.sh cortex-2
```

---

## 5. Compartir archivos con el bot

Para que el bot pueda leer archivos de Google Drive:

1. Abre el archivo o carpeta en Google Drive
2. Clic derecho > **Compartir**
3. Agrega el email del service account (ej: `syn-drive-bot@proyecto.iam.gserviceaccount.com`)
4. Permisos: **Lector**
5. Clic en **Enviar**

Tambien funciona si el archivo es **publico** (cualquiera con el link puede ver).

---

## 6. Comandos del bot en Telegram

| Comando | Funcion |
|---|---|
| `/inicio` | Mensaje de bienvenida |
| `/estado` | Estado del sistema |
| `/archivos` | Ver archivos registrados |
| `/memorias` | Ver memorias guardadas |
| `/recordatorios` | Ver recordatorios programados |
| `/metas` | Ver metas activas |
| `/logs` | Ver actividad del dia |
| `/citas` | Activar/desactivar capturas de prueba |
| `/limpiar` | Limpiar historial de conversacion |
| `/ayuda` | Ver todos los comandos |

Ademas, el bot responde a mensajes normales. Puedes:
- Enviar links de Google Drive para registrar archivos
- Decir "recuerda que..." para guardar memorias
- Pedir recordatorios con hora y fecha
- Crear metas con pasos
- Buscar en internet
- Preguntar sobre el contenido de archivos registrados

---

## 7. Estructura de archivos

```
Cortex-asistente/
├── bot/syn.py              # Bot de Telegram
├── services/
│   ├── drive_service.py    # Lectura de Google Drive
│   ├── openrouter_service.py # Conexion con IA
│   ├── tools.py            # Herramientas del LLM
│   ├── memory_service.py   # Memorias persistentes
│   ├── reminder_service.py # Recordatorios
│   ├── goals_service.py    # Metas y seguimiento
│   └── ...
├── config/settings.py      # Configuracion
├── credentials/            # Service account JSON (NO se sube a git)
├── data/                   # Datos de usuarios (NO se sube a git)
├── .env                    # Variables de entorno (NO se sube a git)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 8. Troubleshooting

### El bot no responde
- Verifica que `TELEGRAM_TOKEN` sea correcto
- Verifica que tu ID este en `ALLOWED_USERS` (o dejalo vacio para permitir todos)
- Revisa logs: `docker compose logs -f`

### "No tengo permisos para acceder al archivo"
- Comparte el archivo/carpeta con el email del service account
- Verifica que la **Google Drive API** este habilitada en el proyecto de Google Cloud

### "Google Drive API has not been used in project..."
- Ve a Google Cloud Console > APIs y servicios > Habilitar APIs
- Busca "Google Drive API" y habilitala
- Espera 1-2 minutos

### Las capturas de Excel se ven mal
- Verifica que LibreOffice este instalado (`soffice --version`)
- En Docker, ya viene incluido en el Dockerfile

### Error de conexion con OpenRouter
- Verifica que `OPENROUTER_API_KEY` sea valida
- Verifica que tengas creditos en OpenRouter

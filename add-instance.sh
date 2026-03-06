#!/bin/bash
set -e

NAME=${1:?"Uso: bash add-instance.sh <nombre> <puerto>"}
PORT=${2:?"Uso: bash add-instance.sh <nombre> <puerto>"}
ENV_FILE=".env.${NAME}"

if [ -f "$ENV_FILE" ]; then
    echo "[!] El archivo $ENV_FILE ya existe."
    echo "    Edita $ENV_FILE y luego ejecuta:"
    echo "    docker compose --profile $NAME up -d --build"
    exit 1
fi

# Crear .env para la nueva instancia
cp .env.example "$ENV_FILE"
echo ""
echo "[+] Archivo $ENV_FILE creado."
echo "    Edita con tus tokens: nano $ENV_FILE"
echo ""

# Agregar servicio al docker-compose.yml
cat >> docker-compose.yml <<EOF

  ${NAME}:
    build: .
    container_name: ${NAME}
    env_file: ${ENV_FILE}
    ports:
      - "${PORT}:8000"
    volumes:
      - ${NAME}-data:/app/data
    restart: unless-stopped
EOF

# Agregar volumen
# Buscar la linea "volumes:" al final y agregar
sed -i "/^volumes:/a\\  ${NAME}-data:" docker-compose.yml

echo "[+] Servicio '${NAME}' agregado en puerto ${PORT}."
echo ""
echo "    Siguiente paso:"
echo "    1. Edita $ENV_FILE con los tokens de esta instancia"
echo "    2. docker compose up -d --build ${NAME}"
echo ""

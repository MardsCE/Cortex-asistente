#!/bin/bash
set -e

NAME=${1:?"Uso: bash add-instance.sh <nombre> <puerto>  (ej: bash add-instance.sh cortex-2 8002)"}
PORT=${2:?"Uso: bash add-instance.sh <nombre> <puerto>  (ej: bash add-instance.sh cortex-2 8002)"}
ENV_FILE=".env.${NAME}"
INSTANCES_FILE=".instances"

# Verificar que no exista ya
if grep -q "^${NAME}:" "$INSTANCES_FILE" 2>/dev/null; then
    echo "[!] La instancia '${NAME}' ya existe."
    echo "    Edita $ENV_FILE y ejecuta: docker compose up -d --build ${NAME}"
    exit 1
fi

# Crear .env para la nueva instancia
if [ ! -f "$ENV_FILE" ]; then
    cp .env.example "$ENV_FILE"
    echo "[+] Archivo $ENV_FILE creado."
else
    echo "[i] $ENV_FILE ya existe, se conserva."
fi

# Registrar la instancia
echo "${NAME}:${PORT}" >> "$INSTANCES_FILE"

# Regenerar docker-compose.yml
bash generate-compose.sh

echo ""
echo "[+] Instancia '${NAME}' registrada en puerto ${PORT}."
echo ""
echo "    Siguiente paso:"
echo "    1. Edita $ENV_FILE con los tokens de esta instancia"
echo "       nano $ENV_FILE"
echo "    2. Levanta la instancia:"
echo "       docker compose up -d --build ${NAME}"
echo ""

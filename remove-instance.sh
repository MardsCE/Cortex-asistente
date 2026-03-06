#!/bin/bash
set -e

NAME=${1:?"Uso: bash remove-instance.sh <nombre>"}
INSTANCES_FILE=".instances"

if ! grep -q "^${NAME}:" "$INSTANCES_FILE" 2>/dev/null; then
    echo "[!] La instancia '${NAME}' no existe."
    exit 1
fi

echo "[*] Deteniendo contenedor ${NAME}..."
docker compose stop "${NAME}" 2>/dev/null || true
docker compose rm -f "${NAME}" 2>/dev/null || true

# Eliminar del registro
sed -i "/^${NAME}:/d" "$INSTANCES_FILE"

# Regenerar docker-compose.yml
bash generate-compose.sh

echo ""
echo "[+] Instancia '${NAME}' eliminada."
echo "    El archivo .env.${NAME} se conserva por seguridad."
echo "    Para eliminar datos: docker volume rm ${NAME}-data"
echo ""

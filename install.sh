#!/bin/bash
set -e

echo "========================================="
echo "  Cortex-asistente - Instalacion VPS"
echo "========================================="
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Docker no encontrado. Instalando..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "[+] Docker instalado."
else
    echo "[+] Docker encontrado."
fi

# Verificar Docker Compose
if ! docker compose version &> /dev/null; then
    echo "[!] Docker Compose no encontrado. Instalando plugin..."
    apt-get update && apt-get install -y docker-compose-plugin
    echo "[+] Docker Compose instalado."
else
    echo "[+] Docker Compose encontrado."
fi

# Crear .env si no existe
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "[!] Archivo .env creado desde .env.example"
    echo "    Edita .env con tus tokens antes de iniciar:"
    echo ""
    echo "    nano .env"
    echo ""
    echo "    Variables requeridas:"
    echo "      TELEGRAM_TOKEN=tu_token_aqui"
    echo "      OPENROUTER_API_KEY=tu_api_key_aqui"
    echo ""
else
    echo "[+] Archivo .env encontrado."
fi

echo ""
echo "========================================="
echo "  Comandos disponibles:"
echo "========================================="
echo ""
echo "  Iniciar:          docker compose up -d --build"
echo "  Ver logs:         docker compose logs -f"
echo "  Detener:          docker compose down"
echo "  Reiniciar:        docker compose restart"
echo ""
echo "  Nueva instancia:  bash add-instance.sh <nombre> <puerto>"
echo ""
echo "========================================="

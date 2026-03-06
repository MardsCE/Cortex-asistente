#!/bin/bash
# Genera docker-compose.yml a partir del registro de instancias (.instances)
set -e

INSTANCES_FILE=".instances"
OUTPUT="docker-compose.yml"

if [ ! -f "$INSTANCES_FILE" ]; then
    echo "[!] No hay instancias registradas. Usa: bash add-instance.sh <nombre> <puerto>"
    exit 1
fi

# Generar servicios
cat > "$OUTPUT" <<'HEADER'
services:
HEADER

VOLUMES=""

while IFS=: read -r name port; do
    [ -z "$name" ] && continue
    env_file=".env.${name}"

    cat >> "$OUTPUT" <<EOF
  ${name}:
    build: .
    container_name: ${name}
    env_file: ${env_file}
    ports:
      - "${port}:8000"
    volumes:
      - ${name}-data:/app/data
    restart: unless-stopped

EOF

    VOLUMES="${VOLUMES}  ${name}-data:\n"
done < "$INSTANCES_FILE"

# Agregar volumes
echo "volumes:" >> "$OUTPUT"
echo -e "$VOLUMES" >> "$OUTPUT"

echo "[+] $OUTPUT generado con $(wc -l < "$INSTANCES_FILE") instancia(s)."

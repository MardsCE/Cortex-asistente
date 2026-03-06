#!/bin/bash
# Lista todas las instancias registradas y su estado
INSTANCES_FILE=".instances"

if [ ! -f "$INSTANCES_FILE" ] || [ ! -s "$INSTANCES_FILE" ]; then
    echo "No hay instancias registradas."
    echo "Usa: bash add-instance.sh <nombre> <puerto>"
    exit 0
fi

echo ""
echo "  Instancias de Cortex"
echo "  ====================="
echo ""
printf "  %-20s %-10s %-15s\n" "NOMBRE" "PUERTO" "ESTADO"
printf "  %-20s %-10s %-15s\n" "------" "------" "------"

while IFS=: read -r name port; do
    [ -z "$name" ] && continue
    # Verificar estado del contenedor
    status=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo "no creado")
    printf "  %-20s %-10s %-15s\n" "$name" "$port" "$status"
done < "$INSTANCES_FILE"

echo ""

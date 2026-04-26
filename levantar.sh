#!/bin/bash
# KraftDo — Levanta todos los paneles del Sistema Universal

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="/tmp"

echo ""
echo "=== KraftDo Sistema Universal ==="
echo ""

# Matar servidores anteriores
pkill -f "php artisan serve" 2>/dev/null
sleep 1

# También levantar la API FastAPI
cd "$BASE_DIR"
if [ -f "docker-compose.dev.yml" ]; then
    docker compose -f docker-compose.dev.yml up -d > /dev/null 2>&1
    echo "✓ API FastAPI → http://192.168.1.11:8000/docs"
fi

# Levantar cada empresa
for empresa in kraftdo_bd adille extractores; do
    dir="$OUTPUT_DIR/${empresa}_test"
    if [ -d "$dir" ]; then
        puerto=$(python3 -c "import hashlib; print(8080 + int(hashlib.md5('$empresa'.encode()).hexdigest(), 16) % 900)")
        cd "$dir"
        php artisan serve --host=0.0.0.0 --port=$puerto > /dev/null 2>&1 &
        nombre=$(python3 -c "import json; c=json.load(open('$BASE_DIR/empresas/$empresa.json')); print(c['empresa']['nombre'])" 2>/dev/null)
        email=$(python3 -c "import json; c=json.load(open('$BASE_DIR/empresas/$empresa.json')); print(c['empresa']['email'])" 2>/dev/null)
        echo "✓ $nombre → http://192.168.1.11:$puerto/admin"
        echo "  Email: $email | Password: kraftdo2026"
    else
        echo "⚠️  $empresa no generado — correr: python3 generator.py $empresa --output $dir"
    fi
done

echo ""
echo "Todos los paneles levantados."
echo ""

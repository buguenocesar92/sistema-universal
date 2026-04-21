#!/bin/bash
# setup_cron.sh — Configura los reportes automáticos semanales en el VPS
# Uso: chmod +x setup_cron.sh && ./setup_cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=$(which python3)

echo "Configurando cron para reportes automáticos..."
echo "Directorio: $SCRIPT_DIR"

# Cargar variables de entorno del .env
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | grep -v '^$' | xargs)
else
    echo "ERROR: No se encontró .env. Copia .env.example a .env y configura las variables."
    exit 1
fi

EMAIL_ADILLE="${EMAIL_ADILLE:-hola@kraftdo.cl}"
EMAIL_EXTRACTORES="${EMAIL_EXTRACTORES:-hola@kraftdo.cl}"

# Agregar crons (lunes 8am para Adille, lunes 8:05am para Extractores)
CRON_ADILLE="0 8 * * 1 cd $SCRIPT_DIR && $PYTHON reporte_adille.py --email $EMAIL_ADILLE >> /var/log/kraftdo_adille.log 2>&1"
CRON_EXTRACTORES="5 8 * * 1 cd $SCRIPT_DIR && $PYTHON reporte_extractores.py --email $EMAIL_EXTRACTORES >> /var/log/kraftdo_extractores.log 2>&1"

# Agregar al crontab sin duplicar
(crontab -l 2>/dev/null | grep -v "reporte_adille\|reporte_extractores"; echo "$CRON_ADILLE"; echo "$CRON_EXTRACTORES") | crontab -

echo ""
echo "✅ Crons configurados:"
echo "   Adille      → lunes 8:00am → $EMAIL_ADILLE"
echo "   Extractores → lunes 8:05am → $EMAIL_EXTRACTORES"
echo ""
echo "Para verificar: crontab -l"
echo "Para logs:      tail -f /var/log/kraftdo_adille.log"

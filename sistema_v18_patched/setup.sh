#!/bin/bash
# setup.sh — Configuración inicial del sistema
# Genera las keys seguras y crea el .env

set -e

if [ -f .env ]; then
    read -p "⚠️  El .env ya existe. ¿Sobreescribir? (y/N): " confirm
    [ "$confirm" != "y" ] && exit 0
fi

echo "Generando keys seguras..."

API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
UPLOAD_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
DB_ROOT_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
N8N_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
N8N_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
APP_KEY="base64:$(python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())")"

cp .env.example .env
sed -i "s|^API_KEY=.*|API_KEY=$API_KEY|"           .env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|"   .env
sed -i "s|^UPLOAD_TOKEN=.*|UPLOAD_TOKEN=$UPLOAD_TOKEN|" .env
sed -i "s|^DB_ROOT_PASS=.*|DB_ROOT_PASS=$DB_ROOT_PASS|" .env
sed -i "s|^DB_PASS=.*|DB_PASS=$DB_PASS|"           .env
sed -i "s|^N8N_PASS=.*|N8N_PASS=$N8N_PASS|"         .env
sed -i "s|^N8N_KEY=.*|N8N_KEY=$N8N_KEY|"           .env
sed -i "s|^APP_KEY=.*|APP_KEY=$APP_KEY|"           .env

echo "✅ .env generado con keys seguras"
echo ""
echo "⚠️  Pendiente configurar manualmente en .env:"
echo "   - SMTP_USER (correo Gmail)"
echo "   - SMTP_PASS (App Password de Gmail)"
echo "   - EMAIL_ADILLE, EMAIL_EXTRACTORES (destinatarios)"
echo "   - ANTHROPIC_API_KEY (para classifier con IA)"
echo ""
echo "Luego ejecutar: docker compose up -d --build"

# ─── Cron de backup diario (3am) ──────────────────────────────────────────────
echo ""
read -p "¿Instalar cron de backup diario a las 3am? (y/N): " instalar_cron
if [ "$instalar_cron" = "y" ]; then
    SCRIPT_ABSOLUTO="$(cd "$(dirname "$0")" && pwd)/cron_backup.sh"
    CRON_LINE="0 3 * * * $SCRIPT_ABSOLUTO >> /var/log/kraftdo_backup.log 2>&1"
    # Evitar duplicados
    (crontab -l 2>/dev/null | grep -v "cron_backup.sh"; echo "$CRON_LINE") | crontab -
    echo "✅ Cron de backup instalado:"
    echo "   $CRON_LINE"
else
    echo "⏭️  Cron de backup no instalado. Para instalarlo manualmente:"
    echo "   crontab -e"
    echo "   # Agregar: 0 3 * * * /opt/kraftdo-sistema/cron_backup.sh >> /var/log/kraftdo_backup.log 2>&1"
fi

echo ""
echo "✅ Setup completo. Proximos pasos:"
echo "   1. Editar .env con SMTP_USER, SMTP_PASS, EMAIL_ADILLE, EMAIL_EXTRACTORES"
echo "   2. docker compose up -d --build"
echo "   3. certbot --nginx -d kraftdo.cl -d api.kraftdo.cl ..."

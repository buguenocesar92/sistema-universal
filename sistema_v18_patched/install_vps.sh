#!/bin/bash
# install_vps.sh — Instalación completa del sistema KraftDo en VPS Ubuntu
# Uso: chmod +x install_vps.sh && sudo ./install_vps.sh
# Requisitos: Ubuntu 22.04+, acceso root

set -e  # Detener si hay error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SISTEMA_DIR="/opt/kraftdo-sistema"
PORTAL_PORT=8002
API_PORT=8000

echo -e "${BLUE}
╔══════════════════════════════════════════════════════╗
║     KraftDo Sistema Universal — Instalador VPS      ║
╚══════════════════════════════════════════════════════╝${NC}"

# ── 1. Dependencias del sistema ────────────────────────────────────────────────
step "1/7 Dependencias del sistema"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx curl git
log "Dependencias instaladas"

# ── 2. Copiar archivos del sistema ─────────────────────────────────────────────
step "2/7 Instalando sistema KraftDo"
mkdir -p $SISTEMA_DIR
cp -r $SCRIPT_DIR/* $SISTEMA_DIR/
chmod +x $SISTEMA_DIR/*.sh 2>/dev/null || true
log "Archivos copiados a $SISTEMA_DIR"

# ── 3. Entorno virtual Python ──────────────────────────────────────────────────
step "3/7 Entorno Python"
cd $SISTEMA_DIR
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q uvicorn python-multipart
log "Dependencias Python instaladas"

# ── 4. Configurar .env ─────────────────────────────────────────────────────────
step "4/7 Configuración"
if [ ! -f "$SISTEMA_DIR/.env" ]; then
    cp $SISTEMA_DIR/.env.example $SISTEMA_DIR/.env
    # Generar keys automáticamente
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    UPLOAD_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
    sed -i "s/^API_KEY=.*/API_KEY=$API_KEY/" $SISTEMA_DIR/.env
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" $SISTEMA_DIR/.env
    echo "UPLOAD_TOKEN=$UPLOAD_TOKEN" >> $SISTEMA_DIR/.env
    warn ".env creado con keys automáticas. Configura SMTP_USER y SMTP_PASS manualmente."
    warn "Archivo: $SISTEMA_DIR/.env"
else
    log ".env ya existe, no se sobreescribe"
fi

# ── 5. Servicios systemd ───────────────────────────────────────────────────────
step "5/7 Servicios del sistema"

# Servicio API
cat > /etc/systemd/system/kraftdo-api.service << EOF
[Unit]
Description=KraftDo API Universal
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$SISTEMA_DIR
EnvironmentFile=$SISTEMA_DIR/.env
ExecStart=$SISTEMA_DIR/venv/bin/python3 api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Servicio Portal de Upload
cat > /etc/systemd/system/kraftdo-portal.service << EOF
[Unit]
Description=KraftDo Upload Portal
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$SISTEMA_DIR
EnvironmentFile=$SISTEMA_DIR/.env
ExecStart=$SISTEMA_DIR/venv/bin/python3 upload_portal.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

chown -R www-data:www-data $SISTEMA_DIR
systemctl daemon-reload
systemctl enable kraftdo-api kraftdo-portal
systemctl start kraftdo-api kraftdo-portal
log "Servicios kraftdo-api y kraftdo-portal activos"

# ── 6. Nginx ───────────────────────────────────────────────────────────────────
step "6/7 Nginx"
cat > /etc/nginx/sites-available/kraftdo-sistema << EOF
server {
    listen 80;
    server_name sistema.kraftdo.cl;

    autoindex off;

    location /storage { deny all; return 403; }
    location ~* \.(env|json|sh|log|sql|py)\$ { deny all; return 403; }

    # Portal de upload (raíz)
    location / {
        proxy_pass http://127.0.0.1:$PORTAL_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        client_max_body_size 11M;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:$API_PORT/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/kraftdo-sistema /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
log "Nginx configurado para sistema.kraftdo.cl"

# ── 7. Cron para reportes automáticos ─────────────────────────────────────────
step "7/7 Reportes automáticos"
source $SISTEMA_DIR/.env
EMAIL_ADILLE_FINAL="${EMAIL_ADILLE:-hola@kraftdo.cl}"
EMAIL_EXT_FINAL="${EMAIL_EXTRACTORES:-hola@kraftdo.cl}"

PYTHON="$SISTEMA_DIR/venv/bin/python3"
CRON1="0 8 * * 1 cd $SISTEMA_DIR && $PYTHON reporte_adille.py --email $EMAIL_ADILLE_FINAL >> /var/log/kraftdo_adille.log 2>&1"
CRON2="5 8 * * 1 cd $SISTEMA_DIR && $PYTHON reporte_extractores.py --email $EMAIL_EXT_FINAL >> /var/log/kraftdo_extractores.log 2>&1"
(crontab -l 2>/dev/null | grep -v "reporte_adille\|reporte_extractores"; echo "$CRON1"; echo "$CRON2") | crontab -
log "Crons configurados (lunes 8am)"

# ── Resumen final ──────────────────────────────────────────────────────────────
echo -e "\n${GREEN}
╔══════════════════════════════════════════════════════╗
║           Instalación completada                    ║
╚══════════════════════════════════════════════════════╝${NC}

${BLUE}URLs:${NC}
  Portal upload:  http://sistema.kraftdo.cl
  API:            http://sistema.kraftdo.cl/api

${BLUE}Próximos pasos:${NC}
  1. Editar $SISTEMA_DIR/.env con SMTP_USER y SMTP_PASS
  2. Obtener SSL: certbot --nginx -d sistema.kraftdo.cl
  3. Reiniciar servicios: systemctl restart kraftdo-api kraftdo-portal

${BLUE}Comandos útiles:${NC}
  Ver logs API:    journalctl -u kraftdo-api -f
  Ver logs portal: journalctl -u kraftdo-portal -f
  Ver logs correo: tail -f /var/log/kraftdo_adille.log
  Estado:          systemctl status kraftdo-api kraftdo-portal
"

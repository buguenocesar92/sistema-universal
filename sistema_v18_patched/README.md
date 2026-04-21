# KraftDo Sistema Universal v18

Plataforma que convierte cualquier Excel en un sistema web operativo.

## Resumen rapido

- **3 empresas configuradas**: Constructora Adille, Extractores Chile, KraftDo SpA
- **24 servicios Docker**: Laravel+Filament, API Python, Classifier AI, Portal, Worker, n8n, MySQL, Redis, Meilisearch, MinIO, Grafana+Prometheus, Uptime Kuma, Reverb (WebSockets), Nginx+Cloudflare
- **142 tests pasando** (Python pytest + Playwright E2E)
- **16 modulos en jobs/**: queue, cache, backup, audit, auth, JWT, 2FA, crypto, rate limit, vault, sentry, i18n, notifications, search, drive export, MJML

## Instalacion

```bash
# 1. Descomprimir
unzip KraftDo_Sistema_v18_completo.zip -d /opt/
cd /opt/sistema_v18_patched

# 2. Generar secrets automaticamente
./setup.sh

# 3. Editar .env con SMTP, EMAIL_ADILLE, EMAIL_EXTRACTORES, etc
nano .env

# 4. Levantar Docker
docker compose up -d --build

# 5. SSL con certbot (primera vez)
docker compose run certbot certonly --webroot -w /var/www/certbot \
  -d kraftdo.cl -d api.kraftdo.cl -d app.kraftdo.cl \
  -d sistema.kraftdo.cl -d n8n.kraftdo.cl \
  -d status.kraftdo.cl -d grafana.kraftdo.cl -d ws.kraftdo.cl
```

## URLs del sistema

| URL | Servicio |
|-----|----------|
| kraftdo.cl/admin | Panel Laravel + Filament |
| api.kraftdo.cl | API REST Python |
| app.kraftdo.cl | Classifier (mapear Excel nuevos) |
| sistema.kraftdo.cl | Portal de upload (Jonathan) |
| n8n.kraftdo.cl | Automatizaciones |
| status.kraftdo.cl | Uptime Kuma |
| grafana.kraftdo.cl | Dashboards de metricas |
| ws.kraftdo.cl | WebSockets (Reverb) |

## Documentacion

- `KraftDo_Manual_Usuario.pdf` - Como usar el sistema
- `KraftDo_Documentacion_Tecnica.pdf` - Arquitectura interna
- `docs/cloudflare_setup.md` - Configurar CDN
- `docs/uptime_kuma_setup.md` - Configurar alertas

## Estructura

```
sistema_v18_patched/
├── core.py, api.py, classifier.py, generator.py
├── onboarding.py, upload_portal.py
├── jobs/              (16 modulos de Sesion 1-4)
├── workers/
├── tests/             (142 tests)
├── docker/
├── laravel_multitenant/
├── empresas/
├── lang/              (es.json, en.json)
├── templates/email/   (MJML)
├── storage/pwa/       (manifest, service worker, tour)
└── .github/workflows/ (CI/CD)
```

## Testing

```bash
# Tests unitarios Python
python3 -m pytest tests/ -v

# Tests E2E (requiere npm install)
npx playwright test
```

## Licencia

Proprietary - KraftDo SpA

---
Contacto: hola@kraftdo.cl

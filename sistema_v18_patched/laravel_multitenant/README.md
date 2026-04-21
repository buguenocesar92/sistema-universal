# KraftDo — Sistema Multi-Tenant Laravel

Un solo Laravel que sirve a las 3 empresas como módulos separados.

## Empresas (tenants)
- `adille`      → Constructora Adille    → /admin/adille
- `extractores` → Extractores Chile Ltda → /admin/extractores  
- `kraftdo_bd`  → KraftDo SpA BD Maestra → /admin/kraftdo

## Instalación en el VPS
```bash
cd /opt/kraftdo-sistema
docker compose up -d --build
docker compose exec laravel php artisan migrate --seed
```

## URLs
- Panel admin:  https://kraftdo.cl/admin
- API Python:   https://api.kraftdo.cl
- Classifier:   https://app.kraftdo.cl
- n8n:          https://n8n.kraftdo.cl
- Upload portal: https://sistema.kraftdo.cl

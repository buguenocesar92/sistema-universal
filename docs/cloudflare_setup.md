# Cloudflare CDN — Configuración

## Paso 1: Agregar el dominio a Cloudflare
1. Entrar a dash.cloudflare.com → Add a Site → `kraftdo.cl`
2. Seleccionar plan Free (es suficiente)
3. Cloudflare escanea los registros DNS existentes

## Paso 2: Cambiar los nameservers en HostGator
1. Ir al panel de HostGator → DNS
2. Cambiar nameservers a los que da Cloudflare (son tipo `xxx.ns.cloudflare.com`)
3. Esperar 24h hasta que propague

## Paso 3: Configurar cada subdominio
Activar "Proxied" (ícono naranja) en todos estos:
- kraftdo.cl → VPS IP
- api.kraftdo.cl → VPS IP
- app.kraftdo.cl → VPS IP
- sistema.kraftdo.cl → VPS IP
- n8n.kraftdo.cl → VPS IP (DESACTIVAR proxy, n8n usa websockets)
- status.kraftdo.cl → VPS IP
- grafana.kraftdo.cl → VPS IP

## Paso 4: SSL/TLS
- Modo: **Full (strict)** — requiere SSL en el VPS también
- Siempre usar HTTPS: ON
- TLS 1.3: ON
- HSTS: ON (con preload si querés)

## Paso 5: Reglas de Firewall (WAF)
Rules → Create Rule:
- Bloquear países: solo si sabés que no van a acceder (NO bloquear CL/AR/MX)
- Rate limiting: 1000 req/min por IP a nivel global

## Paso 6: Cache Rules
Caching → Cache Rules:
- `/admin*`, `/api*` → Bypass cache (dinámico)
- `*.css`, `*.js`, `*.png`, `*.jpg` → Cache Everything (Edge TTL: 1 mes)

## Paso 7: Page Rules
- `*kraftdo.cl/health*` → Cache Level: Bypass
- `*kraftdo.cl/admin*` → Security Level: High

## Resultado esperado
- Latencia menor (cache en ~300 ubicaciones globales)
- Protección DDoS automática
- SSL gratis + renovación automática
- Ancho de banda ilimitado

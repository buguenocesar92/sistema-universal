"""
KraftDo — n8n_generator.py
Genera workflows n8n listos para importar desde el JSON de configuración.

Workflows generados:
  1. bot_{empresa}        → Bot Telegram: cotizador, consultas, guardado en Notion
  2. sync_{empresa}       → Sincronización periódica Excel → base de datos
  3. alertas_{empresa}    → Alertas automáticas (pedidos listos, stock bajo)
  4. reportes_{empresa}   → Reporte semanal automático por email/Telegram

USO:
    python3 n8n_generator.py kraftdo --output ./n8n_workflows
    python3 n8n_generator.py kraftdo --importar   # importa directo a n8n via API
"""

import os
import sys
import json
import uuid
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def new_id() -> str:
    return str(uuid.uuid4())


def nodo_base(tipo: str, nombre: str, x: int, y: int, params: dict = None) -> dict:
    """Genera un nodo n8n con posición y parámetros."""
    return {
        "id":         new_id(),
        "name":       nombre,
        "type":       tipo,
        "typeVersion": 1,
        "position":   [x, y],
        "parameters": params or {},
    }


# ════════════════════════════════════════════════════════════════════════════
# WORKFLOW 1 — Bot Telegram cotizador
# ════════════════════════════════════════════════════════════════════════════
def gen_workflow_bot(cfg: dict, api_url: str) -> dict:
    empresa = cfg["empresa"]["nombre"]
    hojas   = cfg["hojas"]

    # Detectar hojas de catálogo para el menú
    catalogos = [a for a, h in hojas.items() if h.get("tipo") == "catalogo"]
    registros  = [a for a, h in hojas.items() if h.get("tipo") == "registros"]

    menu_items = []
    for i, alias in enumerate(catalogos, 1):
        label = alias.replace("_", " ").title()
        menu_items.append(f"{i}️⃣ {label}")
    menu_items.append(f"{len(catalogos)+1}️⃣ Hablar con el equipo")
    menu_texto = "\n".join(menu_items)

    nodos = []
    conexiones = {}

    # 1. Trigger Telegram
    trigger = nodo_base(
        "n8n-nodes-base.telegramTrigger",
        "📱 Mensaje Telegram",
        100, 300,
        {"updates": ["message"], "additionalFields": {}}
    )
    nodos.append(trigger)

    # 2. Switch por tipo de mensaje
    switch = nodo_base(
        "n8n-nodes-base.switch",
        "🔀 Tipo de mensaje",
        350, 300,
        {
            "dataType": "string",
            "value1":   "={{ $json.message.text }}",
            "rules": {
                "rules": [
                    {"value2": "/start",      "output": 0},
                    {"value2": "1",           "output": 1},
                    {"value2": "2",           "output": 2},
                    {"value2": "cotizar",     "output": 3},
                ]
            },
            "fallbackOutput": 4,
        }
    )
    nodos.append(switch)
    conexiones[trigger["name"]] = {"main": [[{"node": switch["name"], "type": "main", "index": 0}]]}

    # 3. Respuesta menú principal
    menu = nodo_base(
        "n8n-nodes-base.telegram",
        "📋 Enviar menú",
        600, 100,
        {
            "operation": "sendMessage",
            "chatId":    "={{ $json.message.chat.id }}",
            "text":      f"👋 Hola! Soy el asistente de *{empresa}*.\n\n¿En qué te puedo ayudar?\n\n{menu_texto}",
            "additionalFields": {"parse_mode": "Markdown"},
        }
    )
    nodos.append(menu)
    conexiones[switch["name"]] = {"main": [[{"node": menu["name"], "type": "main", "index": 0}]]}

    # 4. HTTP Request al catálogo de la API
    http_catalogo = nodo_base(
        "n8n-nodes-base.httpRequest",
        "🔍 Consultar catálogo API",
        600, 250,
        {
            "method":  "GET",
            "url":     f"{api_url}/kraftdo/catalogo",
            "responseFormat": "json",
        }
    )
    nodos.append(http_catalogo)

    # 5. Formatear y enviar catálogo
    format_cat = nodo_base(
        "n8n-nodes-base.code",
        "📝 Formatear catálogo",
        850, 250,
        {
            "jsCode": """
const data = $input.first().json;
const lineas = [];
for (const [tipo, prods] of Object.entries(data.catalogo || {})) {
  lineas.push(`*${tipo.replace(/_/g,' ').toUpperCase()}*`);
  (prods || []).slice(0, 5).forEach(p => {
    lineas.push(`  ${p.sku} — ${p.producto} — $${(p.precio_1||0).toLocaleString()} CLP`);
  });
  lineas.push('');
}
return [{json: {texto: lineas.join('\\n') || 'Sin productos disponibles'}}];
"""
        }
    )
    nodos.append(format_cat)

    send_cat = nodo_base(
        "n8n-nodes-base.telegram",
        "📦 Enviar catálogo",
        1100, 250,
        {
            "operation": "sendMessage",
            "chatId":    "={{ $('📱 Mensaje Telegram').item.json.message.chat.id }}",
            "text":      "={{ $json.texto }}\n\nPara cotizar escribe: *cotizar SKU cantidad*\nEjemplo: cotizar A01 2",
            "additionalFields": {"parse_mode": "Markdown"},
        }
    )
    nodos.append(send_cat)

    # 6. Cotizador
    cotizador = nodo_base(
        "n8n-nodes-base.code",
        "💰 Parsear cotización",
        600, 400,
        {
            "jsCode": """
const texto = $input.first().json.message?.text || '';
const partes = texto.toLowerCase().replace('cotizar','').trim().split(/\\s+/);
const sku = (partes[0] || '').toUpperCase();
const cantidad = parseInt(partes[1]) || 1;
return [{json: {sku, cantidad, chat_id: $input.first().json.message.chat.id}}];
"""
        }
    )
    nodos.append(cotizador)

    http_precio = nodo_base(
        "n8n-nodes-base.httpRequest",
        "💲 Consultar precio API",
        850, 400,
        {
            "method":  "GET",
            "url":     f"{api_url}/kraftdo/precio",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "sku",      "value": "={{ $json.sku }}"},
                    {"name": "cantidad", "value": "={{ $json.cantidad }}"},
                ]
            },
            "responseFormat": "json",
        }
    )
    nodos.append(http_precio)

    format_precio = nodo_base(
        "n8n-nodes-base.code",
        "📄 Formatear precio",
        1100, 400,
        {
            "jsCode": """
const p = $input.first().json;
if (!p.sku) return [{json: {texto: '❌ SKU no encontrado. Escribe "1" para ver el catálogo.'}}];
const texto = [
  `✅ *${p.producto}* ${p.variante ? '— '+p.variante : ''}`,
  `SKU: ${p.sku} | Cantidad: ${p.cantidad}`,
  `Precio unitario: $${(p.precio_unitario||0).toLocaleString()} CLP`,
  `Subtotal: $${(p.subtotal||0).toLocaleString()} CLP`,
  ``,
  `¿Quieres la cotización completa? Responde *sí*`,
].join('\\n');
return [{json: {texto, sku: p.sku, cantidad: p.cantidad, subtotal: p.subtotal}}];
"""
        }
    )
    nodos.append(format_precio)

    send_precio = nodo_base(
        "n8n-nodes-base.telegram",
        "💬 Enviar precio",
        1350, 400,
        {
            "operation": "sendMessage",
            "chatId":    "={{ $('💰 Parsear cotización').item.json.chat_id }}",
            "text":      "={{ $json.texto }}",
            "additionalFields": {"parse_mode": "Markdown"},
        }
    )
    nodos.append(send_precio)

    # 7. Guardar consulta en Notion
    guardar_notion = nodo_base(
        "n8n-nodes-base.notion",
        "📝 Guardar en Notion",
        1350, 550,
        {
            "operation":  "create",
            "resource":   "databasePage",
            "databaseId": "TU_DATABASE_ID_NOTION",
            "title":      "={{ $('💰 Parsear cotización').item.json.sku }}",
            "propertiesUi": {
                "propertyValues": [
                    {"key": "Estado",   "type": "select",     "selectValue": "Nuevo"},
                    {"key": "SKU",      "type": "rich_text",  "textContent": "={{ $('💰 Parsear cotización').item.json.sku }}"},
                    {"key": "Cantidad", "type": "number",     "numberValue": "={{ $('💰 Parsear cotización').item.json.cantidad }}"},
                    {"key": "Subtotal", "type": "number",     "numberValue": "={{ $json.subtotal }}"},
                    {"key": "Canal",    "type": "select",     "selectValue": "Telegram"},
                ]
            }
        }
    )
    nodos.append(guardar_notion)

    # Conexiones del cotizador
    conexiones[switch["name"]]["main"].append([{"node": cotizador["name"], "type": "main", "index": 0}])  # output 1
    conexiones[switch["name"]]["main"].append([{"node": http_catalogo["name"], "type": "main", "index": 0}])  # output 2
    conexiones[switch["name"]]["main"].append([{"node": cotizador["name"], "type": "main", "index": 0}])  # output 3
    conexiones[http_catalogo["name"]] = {"main": [[{"node": format_cat["name"], "type": "main", "index": 0}]]}
    conexiones[format_cat["name"]]    = {"main": [[{"node": send_cat["name"], "type": "main", "index": 0}]]}
    conexiones[cotizador["name"]]     = {"main": [[{"node": http_precio["name"], "type": "main", "index": 0}]]}
    conexiones[http_precio["name"]]   = {"main": [[{"node": format_precio["name"], "type": "main", "index": 0}]]}
    conexiones[format_precio["name"]] = {"main": [[{"node": send_precio["name"], "type": "main", "index": 0}]]}
    conexiones[send_precio["name"]]   = {"main": [[{"node": guardar_notion["name"], "type": "main", "index": 0}]]}

    return {
        "name":        f"Bot {empresa} — Telegram",
        "nodes":       nodos,
        "connections": conexiones,
        "active":      False,
        "settings":    {"executionOrder": "v1"},
        "tags":        [{"name": "kraftdo"}, {"name": "bot"}],
    }


# ════════════════════════════════════════════════════════════════════════════
# WORKFLOW 2 — Alertas automáticas
# ════════════════════════════════════════════════════════════════════════════
def gen_workflow_alertas(cfg: dict, api_url: str, telegram_chat_id: str) -> dict:
    empresa = cfg["empresa"]["nombre"]
    hojas   = cfg["hojas"]

    # ¿Tiene hojas de pedidos y stock?
    tiene_pedidos = any(a for a, h in hojas.items() if "pedido" in a and h.get("tipo") == "registros")
    tiene_catalogo = any(a for a, h in hojas.items() if h.get("tipo") == "catalogo")

    nodos = []
    conexiones = {}

    # 1. Cron cada hora
    cron = nodo_base(
        "n8n-nodes-base.scheduleTrigger",
        "⏰ Cada hora",
        100, 300,
        {"rule": {"interval": [{"field": "hours", "minutesInterval": 1}]}}
    )
    nodos.append(cron)

    # 2. Verificar pedidos listos
    if tiene_pedidos:
        check_pedidos = nodo_base(
            "n8n-nodes-base.httpRequest",
            "📋 Verificar pedidos",
            350, 200,
            {
                "method": "GET",
                "url":    f"{api_url}/kraftdo/registros/pedidos",
                "sendQuery": True,
                "queryParameters": {"parameters": [{"name": "solo_activos", "value": "true"}]},
                "responseFormat": "json",
            }
        )
        nodos.append(check_pedidos)

        filtrar_listos = nodo_base(
            "n8n-nodes-base.code",
            "🔍 Filtrar listos",
            600, 200,
            {
                "jsCode": """
const registros = $input.first().json.registros || [];
const listos = registros.filter(r => r.estado === 'Listo');
return listos.map(r => ({json: r}));
"""
            }
        )
        nodos.append(filtrar_listos)

        alerta_listo = nodo_base(
            "n8n-nodes-base.telegram",
            "🔔 Alerta pedido listo",
            850, 200,
            {
                "operation": "sendMessage",
                "chatId":    telegram_chat_id,
                "text":      "🟢 *Pedido listo para entregar*\nCliente: {{ $json.cliente }}\nProducto: {{ $json.producto }}\nTotal: ${{ $json.total }}",
                "additionalFields": {"parse_mode": "Markdown"},
            }
        )
        nodos.append(alerta_listo)

        conexiones[cron["name"]]          = {"main": [[{"node": check_pedidos["name"], "type": "main", "index": 0}]]}
        conexiones[check_pedidos["name"]] = {"main": [[{"node": filtrar_listos["name"], "type": "main", "index": 0}]]}
        conexiones[filtrar_listos["name"]]= {"main": [[{"node": alerta_listo["name"],  "type": "main", "index": 0}]]}

    # 3. Verificar stock bajo en catálogos
    if tiene_catalogo:
        check_stock = nodo_base(
            "n8n-nodes-base.httpRequest",
            "📦 Verificar stock",
            350, 400,
            {
                "method": "GET",
                "url":    f"{api_url}/kraftdo/catalogo",
                "responseFormat": "json",
            }
        )
        nodos.append(check_stock)

        filtrar_stock_bajo = nodo_base(
            "n8n-nodes-base.code",
            "⚠️ Stock bajo",
            600, 400,
            {
                "jsCode": """
const data = $input.first().json;
const todos = Object.values(data.catalogo || {}).flat();
const bajos = todos.filter(p => p.stock !== null && p.stock !== undefined && Number(p.stock) < 3);
return bajos.length ? bajos.map(p => ({json: p})) : [{json: {sin_alerta: true}}];
"""
            }
        )
        nodos.append(filtrar_stock_bajo)

        alerta_stock = nodo_base(
            "n8n-nodes-base.telegram",
            "⚠️ Alerta stock bajo",
            850, 400,
            {
                "operation": "sendMessage",
                "chatId":    telegram_chat_id,
                "text":      "⚠️ *Stock bajo*\n{{ $json.sku }} — {{ $json.producto }}\nStock actual: {{ $json.stock }} unidades",
                "additionalFields": {"parse_mode": "Markdown"},
            }
        )
        nodos.append(alerta_stock)

        if not tiene_pedidos:
            conexiones[cron["name"]] = {"main": [[{"node": check_stock["name"], "type": "main", "index": 0}]]}
        else:
            conexiones[cron["name"]]["main"].append([{"node": check_stock["name"], "type": "main", "index": 0}])

        conexiones[check_stock["name"]]         = {"main": [[{"node": filtrar_stock_bajo["name"], "type": "main", "index": 0}]]}
        conexiones[filtrar_stock_bajo["name"]]  = {"main": [[{"node": alerta_stock["name"],       "type": "main", "index": 0}]]}

    return {
        "name":        f"Alertas {empresa} — Automáticas",
        "nodes":       nodos,
        "connections": conexiones,
        "active":      False,
        "settings":    {"executionOrder": "v1"},
        "tags":        [{"name": "kraftdo"}, {"name": "alertas"}],
    }


# ════════════════════════════════════════════════════════════════════════════
# WORKFLOW 3 — Reporte semanal
# ════════════════════════════════════════════════════════════════════════════
def gen_workflow_reporte(cfg: dict, api_url: str, telegram_chat_id: str, email_destino: str) -> dict:
    empresa = cfg["empresa"]["nombre"]

    nodos = []
    conexiones = {}

    # Cron los lunes a las 8am
    cron = nodo_base(
        "n8n-nodes-base.scheduleTrigger",
        "📅 Lunes 8am",
        100, 300,
        {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 8}]}}
    )
    nodos.append(cron)

    # Obtener KPIs
    kpis = nodo_base(
        "n8n-nodes-base.httpRequest",
        "📊 Obtener KPIs",
        350, 300,
        {"method": "GET", "url": f"{api_url}/kraftdo/kpis", "responseFormat": "json"}
    )
    nodos.append(kpis)

    # Obtener pedidos activos
    pedidos = nodo_base(
        "n8n-nodes-base.httpRequest",
        "📋 Pedidos activos",
        350, 450,
        {
            "method": "GET",
            "url":    f"{api_url}/kraftdo/registros/pedidos",
            "sendQuery": True,
            "queryParameters": {"parameters": [{"name": "solo_activos", "value": "true"}]},
            "responseFormat": "json",
        }
    )
    nodos.append(pedidos)

    # Formatear reporte
    formato = nodo_base(
        "n8n-nodes-base.code",
        "📝 Formatear reporte",
        650, 375,
        {
            "jsCode": """
const kpis   = $('📊 Obtener KPIs').first().json;
const ped    = $('📋 Pedidos activos').first().json;
const resumen = kpis.resumen || {};
const hoy = new Date().toLocaleDateString('es-CL');

const reporte = [
  `📊 *Reporte Semanal — ${hoy}*`,
  ``,
  `💰 Saldo en caja:    $${(resumen.saldo_caja||0).toLocaleString()}`,
  `📈 Total vendido:    $${(resumen.total_vendido||0).toLocaleString()}`,
  `🤑 Ganancia total:   $${(resumen.ganancia_total||0).toLocaleString()}`,
  `⚠️  Por cobrar:       $${(resumen.por_cobrar||0).toLocaleString()}`,
  `📦 Pedidos activos:  ${ped.total||0}`,
  ``,
  `Generado automáticamente por KraftDo Sistema`,
].join('\\n');

return [{json: {reporte}}];
"""
        }
    )
    nodos.append(formato)

    # Enviar por Telegram
    tg = nodo_base(
        "n8n-nodes-base.telegram",
        "📱 Reporte Telegram",
        900, 300,
        {
            "operation": "sendMessage",
            "chatId":    telegram_chat_id,
            "text":      "={{ $json.reporte }}",
            "additionalFields": {"parse_mode": "Markdown"},
        }
    )
    nodos.append(tg)

    # Enviar por Email
    email = nodo_base(
        "n8n-nodes-base.emailSend",
        "📧 Reporte Email",
        900, 450,
        {
            "toEmail":  email_destino,
            "subject":  f"Reporte Semanal — {empresa}",
            "text":     "={{ $('📝 Formatear reporte').item.json.reporte }}",
        }
    )
    nodos.append(email)

    conexiones[cron["name"]]   = {"main": [[{"node": kpis["name"], "type": "main", "index": 0}, {"node": pedidos["name"], "type": "main", "index": 0}]]}
    conexiones[kpis["name"]]   = {"main": [[{"node": formato["name"], "type": "main", "index": 0}]]}
    conexiones[pedidos["name"]]= {"main": [[{"node": formato["name"], "type": "main", "index": 0}]]}
    conexiones[formato["name"]]= {"main": [[{"node": tg["name"], "type": "main", "index": 0}, {"node": email["name"], "type": "main", "index": 0}]]}

    return {
        "name":        f"Reporte Semanal — {empresa}",
        "nodes":       nodos,
        "connections": conexiones,
        "active":      False,
        "settings":    {"executionOrder": "v1"},
        "tags":        [{"name": "kraftdo"}, {"name": "reportes"}],
    }



# ════════════════════════════════════════════════════════════════════════════
# WORKFLOW 4 — El Pilar (formulario apoderados)
# ════════════════════════════════════════════════════════════════════════════
def gen_workflow_el_pilar(api_url: str, notion_db_id: str,
                          telegram_viviana: str, email_viviana: str) -> dict:
    """
    Flujo completo para El Pilar 2026:
    Webhook form React → crear fila Notion → Gmail confirma apoderado
    → Telegram alerta Viviana
    """
    nodos = []
    conexiones = {}

    # 1. Webhook desde el formulario React/Laravel
    webhook = nodo_base(
        "n8n-nodes-base.webhook",
        "📥 Form Apoderado",
        100, 300,
        {
            "httpMethod": "POST",
            "path":       "el-pilar-apoderado",
            "responseMode": "onReceived",
        }
    )
    nodos.append(webhook)

    # 2. Validar datos recibidos
    validar = nodo_base(
        "n8n-nodes-base.code",
        "✅ Validar datos",
        350, 300,
        {
            "jsCode": """
const d = $input.first().json.body || $input.first().json;
const errores = [];
if (!d.nombre_alumno)    errores.push('nombre_alumno requerido');
if (!d.nombre_apoderado) errores.push('nombre_apoderado requerido');
if (!d.whatsapp)         errores.push('whatsapp requerido');
if (!d.curso)            errores.push('curso requerido');

if (errores.length > 0) {
  throw new Error('Datos incompletos: ' + errores.join(', '));
}

return [{json: {
  nombre_alumno:    d.nombre_alumno,
  nombre_apoderado: d.nombre_apoderado,
  whatsapp:         d.whatsapp,
  correo:           d.correo || '',
  curso:            d.curso,
  foto_url:         d.foto_url || '',
  timestamp:        new Date().toISOString(),
}}];
"""
        }
    )
    nodos.append(validar)

    # 3. Crear fila en Notion DB El Pilar
    notion = nodo_base(
        "n8n-nodes-base.notion",
        "📝 Registrar en Notion",
        600, 200,
        {
            "operation":  "create",
            "resource":   "databasePage",
            "databaseId": notion_db_id,
            "title":      "={{ $json.nombre_alumno }}",
            "propertiesUi": {
                "propertyValues": [
                    {"key": "Apoderado",  "type": "rich_text",  "textContent": "={{ $json.nombre_apoderado }}"},
                    {"key": "WhatsApp",   "type": "rich_text",  "textContent": "={{ $json.whatsapp }}"},
                    {"key": "Correo",     "type": "email",      "emailValue": "={{ $json.correo }}"},
                    {"key": "Curso",      "type": "select",     "selectValue": "={{ $json.curso }}"},
                    {"key": "Foto URL",   "type": "url",        "urlValue": "={{ $json.foto_url }}"},
                    {"key": "Estado",     "type": "select",     "selectValue": "Recibido"},
                    {"key": "Fecha",      "type": "date",       "dateValue": "={{ $json.timestamp }}"},
                ]
            }
        }
    )
    nodos.append(notion)

    # 4. Gmail confirma al apoderado
    gmail_apoderado = nodo_base(
        "n8n-nodes-base.gmail",
        "📧 Confirmar a apoderado",
        600, 400,
        {
            "operation": "send",
            "toList":    ["={{ $('✅ Validar datos').item.json.correo }}"],
            "subject":   "✅ Datos recibidos — Cuadro de Graduación El Pilar 2026",
            "message":   (
                "Estimado/a {{ $('✅ Validar datos').item.json.nombre_apoderado }},\n\n"
                "Hemos recibido correctamente los datos de {{ $('✅ Validar datos').item.json.nombre_alumno }}.\n\n"
                "En los próximos días nos contactaremos para coordinar los detalles del cuadro NFC.\n\n"
                "Cualquier consulta: hola@kraftdo.cl\n\n"
                "Equipo KraftDo"
            ),
        }
    )
    nodos.append(gmail_apoderado)

    # 5. Telegram avisa a Viviana
    tg_viviana = nodo_base(
        "n8n-nodes-base.telegram",
        "📱 Avisar a Viviana",
        850, 300,
        {
            "operation": "sendMessage",
            "chatId":    telegram_viviana,
            "text": (
                "🎓 *Nuevo registro El Pilar*\n\n"
                "Alumno: {{ $('✅ Validar datos').item.json.nombre_alumno }}\n"
                "Apoderado: {{ $('✅ Validar datos').item.json.nombre_apoderado }}\n"
                "WhatsApp: {{ $('✅ Validar datos').item.json.whatsapp }}\n"
                "Curso: {{ $('✅ Validar datos').item.json.curso }}\n\n"
                "Ver en Notion 👉"
            ),
            "additionalFields": {"parse_mode": "Markdown"},
        }
    )
    nodos.append(tg_viviana)

    # 6. Respuesta webhook al formulario React
    respuesta = nodo_base(
        "n8n-nodes-base.respondToWebhook",
        "✅ Responder al form",
        1100, 300,
        {
            "respondWith": "json",
            "responseBody": '{"ok": true, "mensaje": "Datos registrados correctamente"}',
        }
    )
    nodos.append(respuesta)

    # Conexiones
    conexiones[webhook["name"]]     = {"main": [[{"node": validar["name"],   "type": "main", "index": 0}]]}
    conexiones[validar["name"]]     = {"main": [[{"node": notion["name"],    "type": "main", "index": 0}]]}
    conexiones[notion["name"]]      = {"main": [[
        {"node": gmail_apoderado["name"], "type": "main", "index": 0},
        {"node": tg_viviana["name"],      "type": "main", "index": 0},
    ]]}
    conexiones[tg_viviana["name"]]  = {"main": [[{"node": respuesta["name"], "type": "main", "index": 0}]]}

    return {
        "name":        "El Pilar 2026 — Formulario Apoderados",
        "nodes":       nodos,
        "connections": conexiones,
        "active":      False,
        "settings":    {"executionOrder": "v1"},
        "tags":        [{"name": "kraftdo"}, {"name": "el_pilar"}, {"name": "colegios"}],
    }

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def generar_todos(empresa: str, output_dir: str,
                  api_url: str, telegram_chat_id: str,
                  email_destino: str, importar: bool = False):

    cfg_path = os.path.join(SCRIPT_DIR, "empresas", f"{empresa}.json")
    if not os.path.exists(cfg_path):
        print(f"❌ No encontré: {cfg_path}"); sys.exit(1)

    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    # Workflow El Pilar si la empresa tiene hoja de producción/cuadros
    hojas = cfg.get("hojas", {})
    tiene_pilar = any("pilar" in a.lower() or "cuadro" in a.lower() or "colegio" in a.lower()
                      for a in hojas.keys())

    wf_list = [
        (gen_workflow_bot(cfg, api_url),                              f"bot_{empresa}.json"),
        (gen_workflow_alertas(cfg, api_url, telegram_chat_id),        f"alertas_{empresa}.json"),
        (gen_workflow_reporte(cfg, api_url, telegram_chat_id, email_destino), f"reporte_{empresa}.json"),
    ]

    # Siempre agregar El Pilar si la empresa es kraftdo o tiene hojas de colegios
    if empresa == "kraftdo" or tiene_pilar:
        notion_db = os.environ.get("NOTION_DB_EL_PILAR", "TU_NOTION_DB_ID")
        wf_list.append((
            gen_workflow_el_pilar(api_url, notion_db, telegram_chat_id, email_destino),
            "el_pilar_apoderados.json"
        ))

    workflows = wf_list

    print(f"\n{'='*60}")
    print(f"  n8n Generator — {cfg['empresa']['nombre']}")
    print(f"{'='*60}\n")

    for wf, nombre in workflows:
        path = os.path.join(output_dir, nombre)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
        print(f"  ✅ {nombre} ({len(wf['nodes'])} nodos)")

        if importar:
            n8n_url = os.environ.get("N8N_URL", "http://localhost:5678")
            n8n_key = os.environ.get("N8N_API_KEY", "")
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{n8n_url}/api/v1/workflows",
                    data=json.dumps(wf).encode(),
                    headers={"Content-Type": "application/json", "X-N8N-API-KEY": n8n_key},
                    method="POST"
                )
                with urllib.request.urlopen(req) as resp:
                    print(f"     → Importado a n8n: {json.loads(resp.read())['id']}")
            except Exception as e:
                print(f"     ⚠️  Error importando: {e}")

    print(f"\nPara importar a n8n:")
    print(f"  1. Abre n8n → Workflows → Import")
    print(f"  2. Selecciona los archivos JSON de: {output_dir}")
    print(f"  O usa: python3 n8n_generator.py {empresa} --importar\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KraftDo n8n Generator")
    parser.add_argument("empresa",        help="Nombre empresa (ej: kraftdo)")
    parser.add_argument("--output",       default="./n8n_workflows")
    parser.add_argument("--api-url",      default="http://localhost:8000")
    parser.add_argument("--telegram-id",  default="TU_CHAT_ID")
    parser.add_argument("--email",        default="tu@email.cl")
    parser.add_argument("--importar",     action="store_true", help="Importar directo a n8n")
    args = parser.parse_args()

    generar_todos(
        args.empresa, args.output,
        args.api_url, args.telegram_id,
        args.email, args.importar
    )

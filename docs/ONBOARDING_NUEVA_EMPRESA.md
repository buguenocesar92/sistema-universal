# Onboarding: Nueva Empresa en Sistema Universal

Este documento describe el proceso para integrar una nueva empresa al generador de paneles administrativos.

## 1. Requisitos del Excel
El archivo Excel es la fuente de verdad. Debe cumplir con:
- **Formato**: `.xlsx` (OpenXML).
- **Estructura**: Una hoja por cada entidad (ej: Clientes, Productos, Ventas).
- **Headers**: La primera fila de datos (indicada en `fila_datos`) debe contener los nombres de las columnas.
- **Tipos de Hoja Soportados**:
  - `catalogo`: Tablas de referencia (Maestros) con identificadores únicos.
  - `registros`: Transacciones u operaciones que suelen tener FKs a catálogos.
  - `agregado`: Hojas que consolidan datos de otras (ej: Stock, Resultados).
  - `kpis`: Celdas específicas para indicadores clave.

## 2. Preparación del JSON de Configuración
Crea un archivo en `empresas/nombre_empresa.json`.

### Ejemplo Mínimo Funcional:
```json
{
  "empresa": {
    "nombre": "Mi Nueva Empresa",
    "email": "soporte@empresa.com",
    "color_primary": "2563EB"
  },
  "fuente": {
    "tipo": "local",
    "archivo": "xls/mi_archivo.xlsx"
  },
  "hojas": {
    "productos": {
      "nombre": "Productos",
      "tipo": "catalogo",
      "fila_datos": 2,
      "columnas": {
        "sku": "A",
        "nombre": "B",
        "precio": "C"
      },
      "identificador": "sku"
    },
    "pedidos": {
      "nombre": "Pedidos",
      "tipo": "registros",
      "fila_datos": 2,
      "columnas": {
        "id": "A",
        "fecha": "B",
        "sku": "C",
        "cantidad": "D"
      },
      "identificador": "id"
    }
  }
}
```

## 3. Proceso de Integración
1. **Validación**: Ejecuta `python classifier.py` y sube el Excel para obtener una sugerencia inicial de JSON.
2. **Refinamiento**: Ajusta las letras de las columnas y los tipos de hoja en el JSON generado.
3. **Generación**:
   ```bash
   python generator.py --config mi_empresa.json
   ```
4. **Validación Visual**: Revisa el panel generado en el directorio de salida (por defecto `/tmp/nombre_empresa`).
5. **Despliegue**: Mueve el código a producción o agrégalo a `levantar.sh`.

## 4. Tips Avanzados
- **Relaciones Automáticas**: El sistema detecta que `pedidos.sku` apunta a `productos.sku` si los nombres coinciden o están mapeados.
- **Cálculos**: Define `campos_accessor` en el JSON para traer datos del padre automáticamente (ej: traer el nombre del producto al ver un pedido).
- **Observers**: Si necesitas que un campo se calcule (ej: `total = cantidad * precio`), asegúrate de que el campo destino esté en el JSON y el sistema aplicará las reglas de `generator.py`.
- **Dashboards**: Configura el bloque `"dashboard"` para métricas en tiempo real:

### Ejemplo de Dashboard:
```json
"dashboard": [
  {
    "nombre": "ResumenFinanciero",
    "titulo": "Resumen Financiero",
    "stats": [
      {
        "label": "Ingresos Totales",
        "modelo": "Venta",
        "fn": "sum:total",
        "color": "success",
        "icon": "heroicon-m-banknotes"
      },
      {
        "label": "Venta Promedio",
        "modelo": "Venta",
        "fn": "avg:total",
        "color": "warning"
      },
      {
        "label": "Pedidos Realizados",
        "modelo": "Pedido",
        "fn": "count"
      }
    ]
  }
]
```
> Las funciones soportadas en `fn` son: `count`, `sum:campo` y `avg:campo`. Los campos que contienen "total", "precio", "costo" o "monto" se formatean automáticamente como moneda CLP.

- **Alertas Proactivas**: Configura el bloque `"alertas"` para monitorear condiciones y disparar avisos:

### Ejemplo de Alertas:
```json
"alertas": [
  {
    "nombre": "StockCritico",
    "modelo": "Producto",
    "condicion": "stock < 5",
    "mensaje": "¡Atención! El producto {{nombre}} tiene stock crítico: {{stock}} unidades.",
    "programacion": "hourly"
  },
  {
    "nombre": "CobroPendiente",
    "modelo": "Venta",
    "condicion": "estado = 'Pendiente' AND fecha < NOW() - INTERVAL 7 DAY",
    "mensaje": "La factura {{factura}} de {{empresa}} lleva más de 7 días pendiente.",
    "programacion": "dailyAt('08:00')"
  }
]
```
> Las alertas se registran automáticamente en `routes/console.php` y se ejecutan según la frecuencia indicada en `programacion` (usa métodos nativos de Laravel Scheduler como `hourly()`, `daily()`, `mondays()`, etc). Los mensajes soportan variables entre llaves dobles `{{campo}}`.

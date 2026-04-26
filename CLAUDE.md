# KraftDo Sistema Universal

## Contexto
Generador Python que convierte Excel de PYMEs en paneles web Laravel + Filament 3.
Un solo comando: python3 generator.py {empresa} genera proyecto completo en /tmp.

## Comandos clave
```bash
python3 generator.py kraftdo_bd --output /tmp/kraftdo_bd_test
python3 generator.py adille --output /tmp/adille_test
python3 generator.py extractores --output /tmp/extractores_test
~/Dev/sistema-universal/levantar.sh
```

## Paneles activos
- KraftDo: http://192.168.1.11:8385/admin (hola@kraftdo.cl / kraftdo2026)
- Adille: http://192.168.1.11:8467/admin (contacto@adille.cl / kraftdo2026)
- Extractores: http://192.168.1.11:8397/admin (ventas@extractoreschile.cl / kraftdo2026)

## Reglas críticas
- Filament 3 SIEMPRE — nunca instalar v4
- Modelos en SINGULAR (Producto, Cliente, Pedido)
- $model SIN backslash en Observers PHP
- NO tocar /tmp directamente — usar generator.py
- Excel en xls/ — ruta en .env como EXCEL_DIR

## Archivos importantes
- generator.py — generador principal (v18 estable)
- empresas/*.json — config por empresa
- xls/ — Excel de las 3 empresas
- levantar.sh — levanta los 3 paneles

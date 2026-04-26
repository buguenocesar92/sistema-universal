#!/usr/bin/env python3
"""
Importa datos del Excel al MySQL que usa el panel Filament.
Uso: python3 importar_excel_a_mysql.py kraftdo_bd /tmp/kraftdo_laravel_real
"""
import sys, json, os
import openpyxl
import mysql.connector
from pathlib import Path

def col_letra_a_num(letra):
    result = 0
    for c in letra.upper():
        result = result * 26 + (ord(c) - ord('A') + 1)
    return result

def importar(empresa: str, laravel_dir: str):
    base = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base, "empresas", f"{empresa}.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    excel_path = os.path.join(base, cfg["fuente"]["archivo"])
    wb = openpyxl.load_workbook(excel_path, data_only=True)

    # Leer .env de Laravel para obtener credenciales DB
    env_path = os.path.join(laravel_dir, ".env")
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    conn = mysql.connector.connect(
        host=env.get("DB_HOST", "127.0.0.1"),
        port=int(env.get("DB_PORT", 3306)),
        user=env.get("DB_USERNAME", "kraftdo"),
        password=env.get("DB_PASSWORD", ""),
        database=env.get("DB_DATABASE", "kraftdo")
    )
    cursor = conn.cursor()

    hojas = cfg["hojas"]
    for alias, hoja_cfg in hojas.items():
        tipo = hoja_cfg.get("tipo")
        if tipo not in ("catalogo", "registros"):
            continue

        nombre_hoja = hoja_cfg["nombre"]
        ws = next((wb[h] for h in wb.sheetnames if h == nombre_hoja), None)
        if not ws:
            print(f"  ⚠️  Hoja '{nombre_hoja}' no encontrada")
            continue

        columnas = hoja_cfg["columnas"]
        fila_ini = hoja_cfg.get("fila_datos", 5)
        if tipo == "kpis":
            continue

        # Leer nombre de tabla real desde la migración generada
        import glob, re as _re
        tabla_mysql = None
        patron = os.path.join(laravel_dir, "database", "migrations", f"*create_{alias}*")
        archivos = glob.glob(patron)
        if archivos:
            with open(archivos[0]) as mf:
                m = _re.search(r"Schema::create\(['\"]([\w]+)['\"]", mf.read())
                if m:
                    tabla_mysql = m.group(1)
        if not tabla_mysql:
            # Fallback: plural simple
            tabla_mysql = alias if alias.endswith("s") else alias + "s"
            print(f"  ⚠️  Tabla para {alias} inferida como {tabla_mysql}")

        col_indices = {campo: col_letra_a_num(letra) for campo, letra in columnas.items()}
        campos = list(columnas.keys())

        filas_insertadas = 0
        for row in range(fila_ini, ws.max_row + 1):
            valores = {}
            for campo, idx in col_indices.items():
                val = ws.cell(row, idx).value
                valores[campo] = val

            # Saltar filas completamente vacías
            if all(v is None for v in valores.values()):
                continue

            # Saltar filas con más del 70% de valores vacíos
            total = len(valores)
            vacios = sum(1 for v in valores.values() if v is None or str(v).strip() == "")
            if total > 0 and vacios / total > 0.7:
                continue

            # Saltar filas con palabras de encabezado/totales en cualquier columna
            palabras_skip = ["TOTALES", "TOTAL", "SUBTOTAL", "INGRESAR", "AUTO", "AMARILLO"]
            todos_str = [str(v or "").strip().upper() for v in valores.values()]
            if any(any(p in v for p in palabras_skip) for v in todos_str):
                continue

            # Saltar filas que parecen fórmulas o notas (primer valor empieza con =)
            primer_val = str(list(valores.values())[0] or "").strip()
            if primer_val.startswith("="):
                continue

            # Convertir fechas Excel (datetime → string)
            import datetime as _dt
            for k, v in valores.items():
                # Redondear floats que vienen de fórmulas Excel
                if isinstance(v, float) and v == int(v):
                    valores[k] = int(v)
                elif isinstance(v, float):
                    valores[k] = round(v, 2)
                if isinstance(v, (_dt.datetime, _dt.date)):
                    valores[k] = v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, _dt.datetime) else v.strftime("%Y-%m-%d")

            placeholders = ", ".join(["%s"] * len(campos))
            cols_str = ", ".join([f"`{c}`" for c in campos])
            sql = f"INSERT IGNORE INTO `{tabla_mysql}` ({cols_str}) VALUES ({placeholders})"
            try:
                cursor.execute(sql, [valores.get(c) for c in campos])
                filas_insertadas += 1
            except Exception as e:
                pass  # columna no existe, skip

        conn.commit()
        print(f"  ✓ {tabla_mysql}: {filas_insertadas} registros importados")

    cursor.close()
    conn.close()
    print("\n✅ Importación completada")

if __name__ == "__main__":
    empresa = sys.argv[1] if len(sys.argv) > 1 else "kraftdo_bd"
    laravel_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/kraftdo_laravel_real"
    print(f"\n🔄 Importando {empresa} → {laravel_dir}\n")
    importar(empresa, laravel_dir)

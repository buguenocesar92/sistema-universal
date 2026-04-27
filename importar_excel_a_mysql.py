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

def _construir_mapa_sinonimos(cfg: dict) -> dict:
    """Convierte cfg.sinonimos_modelo {canonico: [variantes]} en un mapa
    plano {variante: canonico, canonico: canonico} para lookup rápido."""
    mapa = {}
    for canonico, variantes in (cfg.get("sinonimos_modelo") or {}).items():
        mapa[canonico] = canonico
        for var in variantes:
            mapa[var] = canonico
    return mapa


def _hojas_que_alimentan_agregado(cfg: dict) -> dict:
    """Devuelve {alias_hoja: campo_grupo_a_canonizar}.

    Para cada hoja tipo "agregado": tanto sus fuentes (el campo_grupo
    en el origen) como la hoja agregada misma (su identificador o
    agrupar_por) deben canonizarse para evitar duplicados.
    """
    mapa = {}
    for alias, hoja in cfg.get("hojas", {}).items():
        if hoja.get("tipo") != "agregado":
            continue
        # La hoja agregada misma: canoniza su agrupar_por / identificador.
        campo_propio = hoja.get("agrupar_por") or hoja.get("identificador")
        if campo_propio:
            mapa[alias] = campo_propio
        for fuente in hoja.get("fuentes", []):
            alias_f  = fuente.get("hoja")
            campo_g  = fuente.get("campo_grupo")
            if alias_f and campo_g:
                mapa[alias_f] = campo_g
    return mapa


def importar(empresa: str, laravel_dir: str):
    base = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base, "empresas", f"{empresa}.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    excel_path = os.path.join(base, cfg["fuente"]["archivo"])
    wb = openpyxl.load_workbook(excel_path, data_only=True)

    sinonimos       = _construir_mapa_sinonimos(cfg)
    canoniza_campos = _hojas_que_alimentan_agregado(cfg)
    if sinonimos:
        print(f"  🔁 sinónimos cargados: {len(sinonimos)} mapeos → "
              f"{set(sinonimos.values())}")

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

    # Pre-pass: hojas tipo matriz_asistencia → despivota a asistencias + pagos_quincena
    for alias, hoja_cfg in hojas.items():
        if hoja_cfg.get("tipo") != "matriz_asistencia":
            continue
        nombre_hoja = hoja_cfg["nombre"]
        ws = next((wb[h] for h in wb.sheetnames if h == nombre_hoja), None)
        if not ws:
            print(f"  ⚠️  Hoja '{nombre_hoja}' no encontrada")
            continue
        mes        = hoja_cfg.get("mes_actual", "")
        f_ini      = hoja_cfg.get("fila_inicio", 5)
        f_fin      = hoja_cfg.get("fila_fin", 18)
        c_codigo   = col_letra_a_num(hoja_cfg.get("col_codigo_obra", "B"))
        c_obra     = col_letra_a_num(hoja_cfg.get("col_obra", "C"))
        c_trab     = col_letra_a_num(hoja_cfg.get("col_trabajador", "D"))
        cols_q1    = [col_letra_a_num(l) for l in hoja_cfg.get("cols_quincena1", [])]
        cols_q2    = [col_letra_a_num(l) for l in hoja_cfg.get("cols_quincena2", [])]
        c_pago_q   = col_letra_a_num(hoja_cfg.get("col_pago_quincena", "T"))
        c_pago_l   = col_letra_a_num(hoja_cfg.get("col_pago_liquidacion", "AH"))

        n_asis = 0
        n_pago = 0
        for fila in range(f_ini, f_fin + 1):
            trabajador = ws.cell(fila, c_trab).value
            if trabajador is None or str(trabajador).strip() == "":
                continue
            trabajador = str(trabajador).strip()
            obra       = ws.cell(fila, c_obra).value
            codigo_obra = ws.cell(fila, c_codigo).value

            # Despivot quincena1 → días 1..15 del mes
            for offset, c in enumerate(cols_q1, start=1):
                v = ws.cell(fila, c).value
                if v is None or str(v).strip() == "":
                    continue
                estado = str(v).strip().upper()[:2]
                fecha = f"{mes}-{offset:02d}"
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO asistencias "
                        "(trabajador, obra, codigo_obra, fecha, mes, estado, created_at, updated_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,NOW(),NOW())",
                        [trabajador, obra, codigo_obra, fecha, mes, estado]
                    )
                    n_asis += 1
                except Exception:
                    pass

            # Despivot quincena2 → días 16..(15+len)
            for offset, c in enumerate(cols_q2, start=16):
                v = ws.cell(fila, c).value
                if v is None or str(v).strip() == "":
                    continue
                estado = str(v).strip().upper()[:2]
                fecha = f"{mes}-{offset:02d}"
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO asistencias "
                        "(trabajador, obra, codigo_obra, fecha, mes, estado, created_at, updated_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,NOW(),NOW())",
                        [trabajador, obra, codigo_obra, fecha, mes, estado]
                    )
                    n_asis += 1
                except Exception:
                    pass

            # Pagos quincena + liquidación
            for periodo, col in [("quincena", c_pago_q), ("liquidacion", c_pago_l)]:
                v = ws.cell(fila, col).value
                if v is None:
                    continue
                try:
                    monto = float(v)
                except (TypeError, ValueError):
                    continue
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO pagos_quincena "
                        "(trabajador, mes, periodo, monto, created_at, updated_at) "
                        "VALUES (%s,%s,%s,%s,NOW(),NOW())",
                        [trabajador, mes, periodo, monto]
                    )
                    n_pago += 1
                except Exception:
                    pass

        conn.commit()
        print(f"  ✓ matriz {nombre_hoja}: {n_asis} asistencias, {n_pago} pagos importados")

    for alias, hoja_cfg in hojas.items():
        tipo = hoja_cfg.get("tipo")
        if tipo not in ("catalogo", "registros", "agregado"):
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
        ident   = hoja_cfg.get("identificador")

        # Palabras que, cuando aparecen como VALOR EXACTO del identificador,
        # marcan filas de header/totales (no datos). Match exacto, no substring,
        # para no descartar conceptos legítimos como "TOTAL BRUTO" si son
        # registros de negocio reales — pero sí filtra filas resumen genéricas.
        SKIP_EXACT = {"TOTALES", "TOTAL", "SUBTOTAL", "INGRESAR DATOS",
                      "[AUTO]", "[INGRESAR]", "AMARILLO"}

        filas_insertadas = 0
        ultimo_ident = None  # carry-forward: filas continuación heredan el identificador
        for row in range(fila_ini, ws.max_row + 1):
            valores = {}
            for campo, idx in col_indices.items():
                val = ws.cell(row, idx).value
                valores[campo] = val

            # 1) Filas completamente vacías
            if all(v is None or str(v).strip() == "" for v in valores.values()):
                continue

            # 2) Si hay identificador definido
            if ident:
                ident_val = valores.get(ident)
                ident_vacio = ident_val is None or str(ident_val).strip() == ""
                if ident_vacio:
                    # Fila continuación: hereda identificador previo si existe.
                    # Si nunca hubo identificador antes, sí saltar.
                    if ultimo_ident is None:
                        continue
                    valores[ident] = ultimo_ident
                else:
                    # 3) Identificador es header de totales exacto
                    s_ident = str(ident_val).strip()
                    if s_ident.upper() in SKIP_EXACT:
                        continue
                    # 3b) Notas a pie / fórmulas explicativas: tienen "=" o son muy largas
                    if "=" in s_ident or len(s_ident) > 50:
                        continue
                    ultimo_ident = ident_val

            # 4) Skip si el primer valor empieza con "="
            primer_val = str(valores.get(ident) if ident else list(valores.values())[0] or "").strip()
            if primer_val.startswith("="):
                continue

            # 5) Canonización de modelo: si esta hoja alimenta a un agregado,
            # mapear el campo_grupo de variante → canónico vía sinonimos.
            campo_canonizar = canoniza_campos.get(alias)
            if campo_canonizar and sinonimos:
                v = valores.get(campo_canonizar)
                if v is not None:
                    s = str(v).strip()
                    if s in sinonimos:
                        valores[campo_canonizar] = sinonimos[s]

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

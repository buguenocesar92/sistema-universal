"""
KraftDo — relations.py
Detecta automáticamente relaciones (foreign keys) entre hojas del JSON.

Estrategias de detección:
  1. Nombre de campo = identificador de otra tabla (pedidos.cliente → clientes.nombre)
  2. Nombre de campo = nombre de otra tabla (pedidos.sku → productos_nfc.sku)
  3. Nombre de campo contiene nombre de otra tabla (pedidos.proveedor → proveedores.proveedor)
"""

import re
from typing import Optional


def tabla(alias: str) -> str:
    return alias.lower().replace("-", "_")


def modelo(alias: str) -> str:
    """Convierte alias a PascalCase singular (mismas reglas que generator.nombre_modelo)."""
    palabras = re.split(r'[_\-\s]+', alias)
    ult = palabras[-1].lower()
    if ult.endswith("ores"):   singular = ult[:-2]
    elif ult.endswith("ales"): singular = ult[:-2]
    elif ult.endswith("iones"): singular = ult[:-2]
    elif ult.endswith("entes"): singular = ult[:-1]
    elif ult.endswith("tes"):  singular = ult[:-1]
    elif ult.endswith("enes"): singular = ult[:-2]
    elif ult.endswith("res"):  singular = ult[:-2]
    elif ult.endswith("nes"):  singular = ult[:-1]
    elif ult.endswith("as"):   singular = ult[:-1]
    elif ult.endswith("os"):   singular = ult[:-1]
    elif ult.endswith("es") and len(ult) > 4: singular = ult[:-1]
    elif ult.endswith("s"):    singular = ult[:-1]
    else: singular = ult
    return "".join(w.capitalize() for w in palabras[:-1]) + singular.capitalize()


def detectar_relaciones(cfg: dict) -> list[dict]:
    """
    Retorna lista de relaciones detectadas:
    [
      {
        "tabla_origen":  "pedidos",
        "campo_origen":  "cliente",
        "tabla_destino": "clientes",
        "campo_destino": "nombre",
        "tipo":          "belongsTo",
        "confianza":     "alta" | "media",
      },
      ...
    ]
    """
    hojas = cfg.get("hojas", {})
    relaciones = []

    # Construir índice: identificador por alias
    idents = {}
    for alias, hoja in hojas.items():
        ident = hoja.get("identificador")
        if ident:
            idents[alias] = ident

    vistos = set()

    for alias_a, hoja_a in hojas.items():
        if hoja_a.get("tipo") not in ("catalogo", "registros"):
            continue
        cols_a = list(hoja_a.get("columnas", {}).keys())

        for campo in cols_a:
            if campo in ("id", "numero", "fecha", "obs", "elaborado", "estado",
                         "canal", "ciudad", "categoria", "cantidad", "total",
                         "precio", "costo", "ganancia", "margen", "margen_pct",
                         "anticipo", "saldo", "dias_rest", "f_entrega"):
                continue

            for alias_b, ident_b in idents.items():
                if alias_a == alias_b:
                    continue

                clave = f"{alias_a}.{campo}→{alias_b}"
                if clave in vistos:
                    continue

                confianza = None
                tabla_b = tabla(alias_b)
                singular_b = tabla_b.rstrip("s")

                # Alta confianza: campo = identificador exacto de otra tabla
                if campo == ident_b and campo in cols_a:
                    confianza = "alta"
                # Alta confianza: campo = nombre de la otra tabla
                elif campo == tabla_b or campo == singular_b:
                    confianza = "alta"
                # Media confianza: campo contiene el nombre de la tabla destino
                elif tabla_b in campo or singular_b in campo:
                    confianza = "media"
                # Media confianza: campo es sku/codigo y tabla_b es un catálogo
                elif campo == "sku" and hoja_a.get("tipo") == "registros" and hojas.get(alias_b, {}).get("tipo") == "catalogo":
                    confianza = "media"

                if confianza:
                    vistos.add(clave)
                    relaciones.append({
                        "tabla_origen":  tabla(alias_a),
                        "modelo_origen": modelo(alias_a),
                        "campo_origen":  campo,
                        "tabla_destino": tabla_b,
                        "modelo_destino": modelo(alias_b),
                        "campo_destino": ident_b,
                        "alias_destino": alias_b,
                        "tipo":          "belongsTo",
                        "confianza":     confianza,
                    })

    return relaciones


def relaciones_por_tabla(relaciones: list[dict]) -> dict[str, list[dict]]:
    """Agrupa relaciones por tabla de origen."""
    resultado = {}
    for rel in relaciones:
        tabla_o = rel["tabla_origen"]
        if tabla_o not in resultado:
            resultado[tabla_o] = []
        resultado[tabla_o].append(rel)
    return resultado


def gen_foreign_keys_migration(relaciones: list[dict], tabla_origen: str) -> str:
    """Genera líneas de foreign key para una migración."""
    lineas = []
    rels = [r for r in relaciones if r["tabla_origen"] == tabla_origen]
    for rel in rels:
        if rel["confianza"] == "alta":
            lineas.append(
                f"            // FK: {rel['campo_origen']} → {rel['tabla_destino']}.{rel['campo_destino']}\n"
                f"            $table->foreign('{rel['campo_origen']}')\n"
                f"                  ->references('{rel['campo_destino']}')\n"
                f"                  ->on('{rel['tabla_destino']}')\n"
                f"                  ->nullOnDelete();"
            )
    return "\n".join(lineas)


def gen_eloquent_relationships(relaciones: list[dict], tabla_origen: str) -> str:
    """Genera métodos de relación para un modelo Eloquent."""
    metodos = []
    rels = [r for r in relaciones if r["tabla_origen"] == tabla_origen]
    for rel in rels:
        nombre_metodo = rel["campo_origen"].rstrip("s")
        if nombre_metodo == rel["campo_origen"]:
            nombre_metodo += "Rel"
        metodos.append(
            f"    public function {nombre_metodo}()\n"
            f"    {{\n"
            f"        return $this->belongsTo(\\App\\Models\\{rel['modelo_destino']}::class,\n"
            f"            '{rel['campo_origen']}', '{rel['campo_destino']}');\n"
            f"    }}"
        )
    return "\n\n".join(metodos)



def gen_hasmany_relationships(relaciones: list, tabla_destino: str, hojas_cfg: dict) -> str:
    """Genera métodos hasMany para el modelo destino de una relación."""
    metodos = []
    ns = "\\App\\Models\\"
    rels_inversas = [r for r in relaciones if r["tabla_destino"] == tabla_destino]
    for rel in rels_inversas:
        nm = rel["tabla_origen"].replace("_", "")
        mo = rel["modelo_origen"]
        co = rel["campo_origen"]
        cd = rel["campo_destino"]
        metodos.append(
            "    public function " + nm + "()\n"
            "    {\n"
            "        return $this->hasMany(" + ns + mo + "::class,\n"
            "            '" + co + "', '" + cd + "');\n"
            "    }"
        )
    return "\n\n".join(metodos)

def gen_filament_select(rel: dict) -> str:
    """Genera un campo Select de Filament para una relación."""
    nombre_metodo = rel["campo_origen"].rstrip("s")
    if nombre_metodo == rel["campo_origen"]:
        nombre_metodo += "Rel"
    return (
        f"                Forms\\Components\\Select::make('{rel['campo_origen']}')\n"
        f"                    ->label('{rel['campo_origen'].replace('_', ' ').capitalize()}')\n"
        f"                    ->relationship('{nombre_metodo}', '{rel['campo_destino']}')\n"
        f"                    ->searchable()\n"
        f"                    ->preload()\n"
        f"                    ->nullable(),"
    )


if __name__ == "__main__":
    import json, sys
    cfg = json.load(open("empresas/kraftdo.json"))
    rels = detectar_relaciones(cfg)
    print(f"\n{len(rels)} relaciones detectadas:\n")
    for r in rels:
        print(f"  [{r['confianza']:5}] {r['tabla_origen']}.{r['campo_origen']} "
              f"→ {r['tabla_destino']}.{r['campo_destino']}")

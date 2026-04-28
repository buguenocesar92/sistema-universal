"""
KraftDo — ai_cleaner.py
Normaliza valores de texto sucios contra una lista de categorías canónicas
usando claude-haiku-3-5. Caché local por (empresa, alias, campo) para
evitar reconsultar la API en cada importación.

USO COMO LIBRERÍA:
    from ai_cleaner import ai_normalizar_columna
    mapeo = ai_normalizar_columna(
        valores_unicos=["Pagado", "PAGADO", "pagado ", "pendient"],
        categorias=["pagado", "pendiente", "rechazado"],
        cache_path="ai_cache/empresa_hoja_campo.json",
    )
    # → {"Pagado": "pagado", "PAGADO": "pagado", "pagado ": "pagado", "pendient": "pendiente"}

Si ANTHROPIC_API_KEY no está disponible, retorna {} con una advertencia
y no rompe el flujo del importer.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path

# Cargar .env de forma defensiva (si python-dotenv no está, leemos a mano).
def _load_env(env_path: str | Path) -> None:
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v


_load_env(Path(__file__).parent / ".env")


MODEL_ID    = "claude-3-5-haiku-latest"   # claude-haiku-3-5
MAX_BATCH   = 200                          # valores por llamada API
SYSTEM_PROMPT = (
    "Eres un normalizador de datos. Dado un valor, devuelve únicamente "
    "el canónico más cercano de la lista. Responde solo con JSON plano "
    "sin markdown, sin texto extra, sin backticks."
)


def _cargar_cache(cache_path: str | Path) -> dict:
    p = Path(cache_path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _guardar_cache(cache_path: str | Path, data: dict) -> None:
    p = Path(cache_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _llamar_api(valores: list[str], categorias: list[str]) -> dict[str, str]:
    """Una llamada a la API. Devuelve {valor_original: canonico}.
    Categorías que no encajan se mapean al original (passthrough).
    """
    try:
        import anthropic
    except ImportError:
        return {}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {}

    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "Categorías canónicas válidas:\n"
        + json.dumps(categorias, ensure_ascii=False)
        + "\n\nValores de entrada (clasifica cada uno al canónico más cercano):\n"
        + json.dumps(valores, ensure_ascii=False)
        + "\n\nResponde con un JSON {valor_original: canónico}. Si un valor no "
        "encaja en ninguna categoría, devuelve el valor original como canónico."
    )

    try:
        resp = client.messages.create(
            model=MODEL_ID,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = resp.content[0].text.strip()
        # El modelo puede devolver el JSON envuelto o limpio.
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}
        # Garantizar que solo retornamos categorías válidas o passthrough.
        cats_set = set(categorias)
        return {
            str(k): (str(v) if str(v) in cats_set else str(k))
            for k, v in data.items()
        }
    except Exception as e:
        print(f"  ⚠️  ai_cleaner: error en API ({e.__class__.__name__}); "
              f"se usará passthrough.")
        return {}


def ai_normalizar_columna(
    valores_unicos: list[str],
    categorias: list[str],
    cache_path: str,
    campo: str = "(campo)",
) -> dict[str, str]:
    """Mapea cada valor único al canónico más cercano usando IA + caché.

    Args:
        valores_unicos: lista de strings tal como vienen del Excel.
        categorias: lista de canónicos válidos.
        cache_path: ruta a archivo JSON con el mapeo persistido.
        campo: nombre del campo para el reporte impreso.

    Returns:
        dict {valor_original: canónico}. Si la API no está disponible
        (sin ANTHROPIC_API_KEY o paquete `anthropic`), devuelve {} y
        loggea una advertencia — el importer hará passthrough.
    """
    valores_dedup = []
    seen: set[str] = set()
    for v in valores_unicos:
        if v is None:
            continue
        s = str(v).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        valores_dedup.append(s)

    n_unicos = len(valores_dedup)
    if not valores_dedup or not categorias:
        return {}

    cache = _cargar_cache(cache_path)

    # Resolver desde caché
    desde_cache = {v: cache[v] for v in valores_dedup if v in cache}
    pendientes  = [v for v in valores_dedup if v not in cache]

    api_calls = 0
    api_resultado: dict[str, str] = {}

    if pendientes:
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            print(f"  ⚠️  ai_cleaner: ANTHROPIC_API_KEY no configurada "
                  f"({len(pendientes)} valores no canonizados).")
            return {**desde_cache}

        # Lotes de hasta MAX_BATCH valores por llamada
        for i in range(0, len(pendientes), MAX_BATCH):
            lote = pendientes[i:i + MAX_BATCH]
            mapeo_lote = _llamar_api(lote, categorias)
            api_calls += 1
            if not mapeo_lote:
                # Falló la llamada: passthrough para este lote
                for v in lote:
                    api_resultado[v] = v
            else:
                # Asegurar que cada valor enviado tenga respuesta
                for v in lote:
                    api_resultado[v] = mapeo_lote.get(v, v)

        # Persistir caché incrementalmente
        cache.update(api_resultado)
        _guardar_cache(cache_path, cache)

    resultado = {**desde_cache, **api_resultado}
    n_categorias_distintas = len(set(resultado.values()))
    print(
        f"  🤖 {campo}: {n_unicos} valores → {n_categorias_distintas} categorías "
        f"({n_unicos} únicos, {len(desde_cache)} desde caché, {api_calls} API calls)"
    )
    return resultado


# ────────────────────────────────────────────────────────────
# CLI mínima: smoke test sin tocar Excel real.
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ai_cleaner — smoke test")
    parser.add_argument("--cache", default="ai_cache/_smoke_test.json")
    parser.add_argument("--cats",  default="pagado,pendiente,rechazado,anulado")
    parser.add_argument("--vals",  default="Pagado,PAGADO,pendient,Anulada,xxxxx")
    args = parser.parse_args()
    out = ai_normalizar_columna(
        valores_unicos=args.vals.split(","),
        categorias=args.cats.split(","),
        cache_path=args.cache,
        campo="smoke",
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))

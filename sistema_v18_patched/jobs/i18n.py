"""
i18n.py — Sistema simple de traducciones
Uso:  t("portal.titulo", lang="es")
      t("portal.titulo", lang="en")
"""
import json, os
from pathlib import Path
from functools import lru_cache

LANG_DIR     = Path(__file__).parent.parent / "lang"
DEFAULT_LANG = os.environ.get("DEFAULT_LANG", "es")

@lru_cache(maxsize=10)
def _cargar(lang: str) -> dict:
    """Carga un archivo de idioma, cacheado."""
    path = LANG_DIR / f"{lang}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def t(clave: str, lang: str = None, **kwargs) -> str:
    """
    Traduce una clave con notación de puntos.

    Ejemplos:
        t("portal.titulo")
        t("errores.extension_invalida", lang="en")
        t("reportes.enviado", lang="es")  # usa español por defecto
    """
    lang = lang or DEFAULT_LANG
    datos = _cargar(lang)

    # Navegar por la clave con puntos
    partes = clave.split(".")
    for parte in partes:
        if isinstance(datos, dict):
            datos = datos.get(parte, "")
        else:
            return clave  # no encontrada, devolver la clave

    if isinstance(datos, str):
        # Soporte para interpolación: t("welcome", name="Jonathan") → "Hola Jonathan"
        try:
            return datos.format(**kwargs) if kwargs else datos
        except KeyError:
            return datos
    return clave


def idiomas_disponibles() -> list[str]:
    """Lista idiomas con archivo de traducción."""
    return [f.stem for f in LANG_DIR.glob("*.json")]

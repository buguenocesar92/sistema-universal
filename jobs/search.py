"""
search.py — Búsqueda full-text con Meilisearch
Indexa automáticamente productos, clientes, pedidos de todas las empresas.
"""
import os
from typing import Optional

MEILI_URL    = os.environ.get("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY    = os.environ.get("MEILI_MASTER_KEY", "")

try:
    import meilisearch
    _client = meilisearch.Client(MEILI_URL, MEILI_KEY) if MEILI_KEY else meilisearch.Client(MEILI_URL)
    _client.health()
    MEILI_OK = True
except Exception:
    _client = None
    MEILI_OK = False


def indexar_empresa(empresa: str, registros: dict):
    """
    Indexa todos los registros de una empresa en Meilisearch.

    Args:
        empresa: slug de la empresa
        registros: {"productos": [...], "clientes": [...], ...}
    """
    if not MEILI_OK:
        return {"error": "Meilisearch no disponible"}

    resultados = {}
    for hoja, datos in registros.items():
        if not datos or not isinstance(datos, list):
            continue

        index_name = f"{empresa}_{hoja}"
        documentos = []
        for i, r in enumerate(datos):
            if not isinstance(r, dict):
                continue
            # Cada documento necesita un id único
            doc = dict(r)
            doc["id"] = doc.get("id") or doc.get("sku") or doc.get("numero") or f"{empresa}_{hoja}_{i}"
            doc["id"] = str(doc["id"]).replace("-", "_")
            doc["_empresa"] = empresa
            doc["_hoja"] = hoja
            documentos.append(doc)

        if documentos:
            index = _client.index(index_name)
            task = index.add_documents(documentos)
            resultados[hoja] = {"indexados": len(documentos), "task": task.task_uid}

    return resultados


def buscar(empresa: str, query: str, hoja: Optional[str] = None, limit: int = 20):
    """
    Busca en una empresa específica, opcionalmente en una hoja.

    Ejemplo:
        buscar("adille", "materiales obra GYM", hoja="materiales")
        buscar("extractores", "EXT-60W")  # busca en todas las hojas
    """
    if not MEILI_OK:
        return {"error": "Meilisearch no disponible", "hits": []}

    if hoja:
        # Buscar solo en una hoja
        index = _client.index(f"{empresa}_{hoja}")
        res = index.search(query, {"limit": limit})
        return {
            "query":  query,
            "empresa": empresa,
            "hoja":    hoja,
            "total":   res["estimatedTotalHits"],
            "hits":    res["hits"],
        }
    else:
        # Buscar en todas las hojas de la empresa
        indices = [i["uid"] for i in _client.get_indexes()["results"] if i["uid"].startswith(f"{empresa}_")]
        todos = []
        for idx_name in indices:
            try:
                idx = _client.index(idx_name)
                res = idx.search(query, {"limit": limit // max(len(indices), 1)})
                for hit in res["hits"]:
                    hit["_index"] = idx_name
                    todos.append(hit)
            except Exception:
                continue
        return {
            "query":   query,
            "empresa": empresa,
            "total":   len(todos),
            "hits":    todos[:limit],
        }


def reindexar_todo():
    """Re-indexa todas las empresas. Útil después de un backup/restore."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import Sistema
    from pathlib import Path
    import json

    empresas_dir = Path(__file__).parent.parent / "empresas"
    resultados = {}

    for cfg_file in empresas_dir.glob("*.json"):
        empresa = cfg_file.stem
        try:
            s = Sistema(empresa)
            datos = {}
            for hoja in s.hojas_disponibles():
                cfg_hoja = s.cfg["hojas"][hoja]
                if cfg_hoja.get("tipo") != "kpis":
                    try:
                        datos[hoja] = s.registros(hoja)
                    except Exception:
                        pass
            resultados[empresa] = indexar_empresa(empresa, datos)
        except Exception as e:
            resultados[empresa] = {"error": str(e)}

    return resultados


def estadisticas():
    """Devuelve stats de todos los índices."""
    if not MEILI_OK:
        return {"error": "Meilisearch no disponible"}
    try:
        indices = _client.get_indexes()["results"]
        return {
            "total_indices": len(indices),
            "indices":       [{"uid": i["uid"], "docs": i.get("numberOfDocuments", 0)} for i in indices],
        }
    except Exception as e:
        return {"error": str(e)}

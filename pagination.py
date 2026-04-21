"""
pagination.py — Paginación con cursor para endpoints de registros

El problema del limit/offset clásico: si hay 100k filas y pedís offset=99000,
MySQL tiene que saltar 99k filas. Lento.

La solución profesional es paginación con cursor: en vez de offset,
el cliente recibe un "cursor" (puntero) y pide "dame los siguientes N después de X".

Uso:
    from pagination import paginar
    
    resultado = paginar(
        datos=lista_registros,
        cursor=request.query_params.get("cursor"),
        limit=100
    )
    return {
        "registros": resultado["items"],
        "next_cursor": resultado["next_cursor"],
        "has_more": resultado["has_more"],
    }
"""
import base64
import json
from typing import Any, Optional

def encode_cursor(pos: int) -> str:
    return base64.urlsafe_b64encode(
        json.dumps({"pos": pos}).encode()
    ).decode().rstrip("=")

def decode_cursor(cursor: str) -> int:
    try:
        # Agregar padding si falta
        padded = cursor + "=" * (4 - len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
        return int(data.get("pos", 0))
    except:
        return 0

def paginar(datos: list,
            cursor: Optional[str] = None,
            limit: int = 100) -> dict:
    """
    Retorna {items, next_cursor, has_more, total}.
    
    Si el cliente no pasa cursor, arranca desde 0.
    Si hay más items, devuelve next_cursor para el siguiente request.
    """
    limit = max(1, min(limit, 500))   # limit entre 1 y 500
    start = decode_cursor(cursor) if cursor else 0
    end   = start + limit

    items = datos[start:end]
    has_more    = end < len(datos)
    next_cursor = encode_cursor(end) if has_more else None

    return {
        "items":       items,
        "next_cursor": next_cursor,
        "has_more":    has_more,
        "total":       len(datos),
        "limit":       limit,
    }

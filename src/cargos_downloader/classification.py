"""Clasificacion unica de documentos por origen y usuario que registra.

La usan la persistencia, el Excel y la organizacion de adjuntos para que un
documento nunca quede clasificado de forma distinta en cada salida.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ORIGIN_OFFICE = "oficina"
ORIGIN_PERSONAL = "personal"
ORIGIN_MANUAL = "manual"
ORIGIN_PIDE = "pide"
ORIGIN_UNCLASSIFIED = "sin_clasificar"

EXTERNAL_ORIGINS = frozenset({ORIGIN_MANUAL, ORIGIN_PIDE})

ORIGIN_LABELS = {
    ORIGIN_OFFICE: "Oficina",
    ORIGIN_PERSONAL: "Personal",
    ORIGIN_MANUAL: "Manual/Externo",
    ORIGIN_PIDE: "Interoperabilidad/PIDE",
    ORIGIN_UNCLASSIFIED: "Sin clasificar",
}


@dataclass(frozen=True)
class Classification:
    group: str
    registrant_id: str | None
    issue: str | None = None


def classify_document(document: dict[str, Any]) -> Classification:
    """Clasifica con `docu_origen`, `docu_tipo` y `docu_idusuario`.

    `oper_idusuario` es un respaldo temporal solo cuando `docu_idusuario` esta
    ausente o es nulo. Un documento personal sin usuario valido queda sin
    clasificar; en oficina y externos el usuario es informativo.
    """
    registrant_id, user_issue = _registrant(document)

    origin_value = document.get("docu_origen")
    if origin_value is None or not str(origin_value).strip():
        return Classification(ORIGIN_UNCLASSIFIED, registrant_id, "docu_origen ausente o vacío")
    try:
        origin = int(origin_value)
    except (TypeError, ValueError):
        return Classification(ORIGIN_UNCLASSIFIED, registrant_id, "docu_origen no es numérico")
    if origin == 2:
        return Classification(ORIGIN_MANUAL, registrant_id)
    if origin == 3:
        return Classification(ORIGIN_PIDE, registrant_id)
    if origin != 1:
        return Classification(
            ORIGIN_UNCLASSIFIED, registrant_id, f"docu_origen no reconocido ({origin})"
        )

    if "docu_tipo" not in document:
        return Classification(
            ORIGIN_UNCLASSIFIED, registrant_id, "docu_tipo ausente para docu_origen=1"
        )
    kind_value = document["docu_tipo"]
    if kind_value is None:
        kind = 0
    else:
        if not str(kind_value).strip():
            return Classification(
                ORIGIN_UNCLASSIFIED, registrant_id, "docu_tipo vacío para docu_origen=1"
            )
        try:
            kind = int(kind_value)
        except (TypeError, ValueError):
            return Classification(
                ORIGIN_UNCLASSIFIED, registrant_id, "docu_tipo no es numérico para docu_origen=1"
            )
    if kind == 0:
        return Classification(ORIGIN_OFFICE, registrant_id)
    if kind != 1:
        return Classification(
            ORIGIN_UNCLASSIFIED,
            registrant_id,
            f"docu_tipo no reconocido ({kind}) para docu_origen=1",
        )
    if user_issue:
        return Classification(ORIGIN_UNCLASSIFIED, None, f"{user_issue} en documento personal")
    return Classification(ORIGIN_PERSONAL, registrant_id)


def registrant_label(registrant_id: str | None, names: dict[str, str]) -> str:
    """Texto visible de quien registra: `30 - ANA PEREZ`, solo `30` o vacio.

    El nombre solo se agrega si `names` lo confirma sin duda; si no, basta el ID.
    """
    if not registrant_id:
        return ""
    name = names.get(registrant_id, "").strip()
    return f"{registrant_id} - {name}" if name else registrant_id


def _registrant(document: dict[str, Any]) -> tuple[str | None, str | None]:
    value = document.get("docu_idusuario")
    field = "docu_idusuario"
    if value is None:
        value = document.get("oper_idusuario")
        field = "oper_idusuario"
    if value is None or not str(value).strip():
        return None, "docu_idusuario y oper_idusuario ausentes o vacíos"
    if isinstance(value, bool):
        return None, f"{field} no es un identificador válido"
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{field} no es numérico"
    if number <= 0:
        return None, f"{field} no es positivo"
    return str(number), None

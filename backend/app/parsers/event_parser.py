"""Parser de líneas de log que representan eventos de aplicación."""

import re
from typing import Optional

from .base_parser import BaseParser, ParsedRecord

# Líneas con palabra clave EVENT
_RE_EVENTO = re.compile(
    r"^\[?(?P<dt>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\]?\s+"
    r"\[?EVENTS?\]?\s+"
    r"(?:(?P<componente>[\w][\w.\-/]*)\s+-\s+)?"
    r"(?P<tipo>[\w][\w.\-/]*)"
    r"(?:\s+user=(?P<usuario>\S+))?"
    r"(?:\s+component=(?P<comp2>\S+))?"
    r"(?:\s+-\s+(?P<descripcion>.+))?$",
    re.IGNORECASE,
)

# Líneas con tipo_evento explícito como clave=valor
_RE_EVENTO_KV = re.compile(
    r"^\[?(?P<dt>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\]?\s+"
    r"\[?EVENTS?\]?\s+"
    r"(?P<tipo>[\w][\w.\-/]*)"
    r"(?:.*user=(?P<usuario>\S+))?"
    r"(?:.*component=(?P<componente>\S+))?"
    r"(?:.*description=(?P<descripcion>.+))?$",
    re.IGNORECASE,
)

PATRONES = [_RE_EVENTO, _RE_EVENTO_KV]


class EventParser(BaseParser):
    """Parser especializado en líneas de log que representan eventos de aplicación."""

    def puede_parsear(self, muestra: str) -> bool:
        """Devuelve True si la muestra contiene al menos una línea de evento reconocible."""
        for linea in muestra.splitlines():
            if any(p.match(linea) for p in PATRONES):
                return True
        return False

    def parsear_linea(
        self, linea: str, num_linea: int, origen: str
    ) -> Optional[ParsedRecord]:
        """Parsea una línea de log y devuelve ParsedRecord si representa un evento."""
        m = _RE_EVENTO.match(linea)
        if not m:
            m = _RE_EVENTO_KV.match(linea)
        if not m:
            return None

        grupos = m.groupdict()
        componente = grupos.get("componente") or grupos.get("comp2")
        descripcion = grupos.get("descripcion") or linea

        return ParsedRecord(
            tabla_destino="t_eventos",
            datos={
                "fecha_hora": self._parse_dt(grupos["dt"]),
                "tipo_evento": grupos["tipo"],
                "descripcion": descripcion.strip(),
                "usuario": grupos.get("usuario") or None,
                "componente": componente or None,
                "origen_fichero": origen,
                "num_linea": num_linea,
            },
            num_linea=num_linea,
            origen_fichero=origen,
        )

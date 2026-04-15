"""Parser de líneas de log que contienen métricas numéricas."""

import re
from typing import Optional

from .base_parser import BaseParser, ParsedRecord

# Líneas que contienen la palabra clave METRIC/METRICS
_RE_METRICA = re.compile(
    r"^(?P<dt>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\s+"
    r"\[?METRICS?\]?\s+"
    r"(?:(?P<componente>[\w][\w.\-/]*)\s+-\s+)?"
    r"(?P<nombre>[\w][\w.\-/]*)\s*[=:]\s*"
    r"(?P<valor>-?\d+(?:[.,]\d+)?)"
    r"(?:\s+(?P<unidad>[^\s]+))?",
    re.IGNORECASE,
)

# Líneas con formato clave=valor numérico en cualquier nivel de log
_RE_KV_NUMERICO = re.compile(
    r"^(?P<dt>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\s+"
    r"\[?(?:INFO|DEBUG|TRACE)\]?\s+"
    r"(?:(?P<componente>[\w][\w.\-/]*)\s+-\s+)?"
    r"(?P<nombre>[\w][\w.\-/]*)\s*[=:]\s*"
    r"(?P<valor>-?\d+(?:[.,]\d+)?)"
    r"(?:\s+(?P<unidad>[^\s]+))?$",
    re.IGNORECASE,
)

PATRONES = [_RE_METRICA, _RE_KV_NUMERICO]


class MetricsParser(BaseParser):
    """Parser especializado en líneas de log que contienen métricas numéricas."""

    def puede_parsear(self, muestra: str) -> bool:
        """Devuelve True si la muestra contiene al menos una línea de métrica reconocible."""
        for linea in muestra.splitlines():
            if any(p.match(linea) for p in PATRONES):
                return True
        return False

    def parsear_linea(
        self, linea: str, num_linea: int, origen: str
    ) -> Optional[ParsedRecord]:
        """Parsea una línea de log y devuelve ParsedRecord si contiene una métrica numérica."""
        for patron in PATRONES:
            m = patron.match(linea)
            if not m:
                continue
            try:
                valor = float(m.group("valor").replace(",", "."))
            except ValueError:
                continue
            return ParsedRecord(
                tabla_destino="t_metricas",
                datos={
                    "fecha_hora": self._parse_dt(m.group("dt")),
                    "nombre_metrica": m.group("nombre"),
                    "valor": valor,
                    "unidad": m.group("unidad") or None,
                    "componente": m.groupdict().get("componente") or None,
                    "origen_fichero": origen,
                    "num_linea": num_linea,
                },
                num_linea=num_linea,
                origen_fichero=origen,
            )
        return None

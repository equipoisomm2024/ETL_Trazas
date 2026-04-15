"""Parser de líneas de log con nivel de error (ERROR, WARN, CRITICAL, FATAL)."""

import re
from typing import Optional

from .base_parser import BaseParser, ParsedRecord

NIVELES_ERROR = {"ERROR", "WARN", "WARNING", "CRITICAL", "FATAL"}

# Patrones soportados (del más específico al más general)
PATRONES = [
    # [2026-04-13T08:45:12] NIVEL - mensaje
    re.compile(
        r"^\[(?P<dt>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\]\s+"
        r"(?P<nivel>ERROR|WARN(?:ING)?|CRITICAL|FATAL|INFO|DEBUG)\s+-\s+"
        r"(?P<mensaje>.+)$",
        re.IGNORECASE,
    ),
    # 2026-04-13 08:45:12,345 [NIVEL] componente - mensaje
    # 2026-04-13 08:45:12 NIVEL componente - mensaje
    re.compile(
        r"^(?P<dt>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\s+"
        r"\[?(?P<nivel>ERROR|WARN(?:ING)?|CRITICAL|FATAL|INFO|DEBUG)\]?\s+"
        r"(?:(?P<componente>[\w][\w.\-/]*)\s+-\s+|-\s+)?(?P<mensaje>.+)$",
        re.IGNORECASE,
    ),
]


class ErrorParser(BaseParser):
    """Parser especializado en líneas de log con niveles de error/alerta."""

    def puede_parsear(self, muestra: str) -> bool:
        """Devuelve True si la muestra contiene al menos una línea de nivel error."""
        for linea in muestra.splitlines():
            for patron in PATRONES:
                m = patron.match(linea)
                if m and m.group("nivel").upper() in NIVELES_ERROR:
                    return True
        return False

    def parsear_linea(
        self, linea: str, num_linea: int, origen: str
    ) -> Optional[ParsedRecord]:
        """Parsea una línea de log y devuelve ParsedRecord solo para niveles de error."""
        for patron in PATRONES:
            m = patron.match(linea)
            if not m:
                continue
            nivel_raw = m.group("nivel").upper()
            if nivel_raw not in NIVELES_ERROR:
                return None
            nivel = _normalizar_nivel(nivel_raw)
            componente = m.groupdict().get("componente")
            return ParsedRecord(
                tabla_destino="t_errores",
                datos={
                    "fecha_hora": self._parse_dt(m.group("dt")),
                    "nivel": nivel,
                    "mensaje": m.group("mensaje"),
                    "componente": componente or None,
                    "origen_fichero": origen,
                    "num_linea": num_linea,
                },
                num_linea=num_linea,
                origen_fichero=origen,
            )
        return None


def _normalizar_nivel(nivel: str) -> str:
    """Normaliza variantes de nivel a valor canónico."""
    if nivel == "WARNING":
        return "WARN"
    if nivel == "FATAL":
        return "ERROR"
    return nivel

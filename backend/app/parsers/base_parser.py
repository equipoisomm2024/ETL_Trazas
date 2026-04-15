"""Clase abstracta BaseParser y dataclass ParsedRecord."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional


@dataclass
class ParsedRecord:
    """Registro extraído de una línea de log, listo para inserción en BD."""

    tabla_destino: str       # 't_errores' | 't_metricas' | 't_eventos'
    datos: dict              # Campos extraídos listos para inserción
    num_linea: int           # Línea de origen en el fichero
    origen_fichero: str      # Ruta absoluta del fichero procesado


class BaseParser(ABC):
    """Interfaz común para todos los parsers de log."""

    @abstractmethod
    def puede_parsear(self, muestra: str) -> bool:
        """Devuelve True si este parser reconoce el formato de la muestra."""

    @abstractmethod
    def parsear_linea(
        self, linea: str, num_linea: int, origen: str
    ) -> Optional[ParsedRecord]:
        """Parsea una línea. Devuelve None si no aplica o no es relevante."""

    def parsear_fichero(
        self, ruta: str, desde_linea: int = 0
    ) -> Iterator[ParsedRecord]:
        """Itera el fichero desde desde_linea, yielding ParsedRecord por cada línea reconocida."""
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            for i, linea in enumerate(f, start=1):
                if i <= desde_linea:
                    continue
                record = self.parsear_linea(linea.rstrip(), i, ruta)
                if record:
                    yield record

    def _parse_dt(self, texto: str) -> Optional[datetime]:
        """Convierte cadena de fecha/hora a datetime. Devuelve None si no se reconoce el formato."""
        texto = texto.strip()
        # Normalizar separador de milisegundos y 'T' como separador de fecha/hora
        texto_norm = texto.replace(",", ".").replace("T", " ")
        formatos = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(texto_norm, fmt)
            except ValueError:
                continue
        return None

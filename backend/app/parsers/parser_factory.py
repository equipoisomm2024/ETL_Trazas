"""Factory para selección automática o explícita del parser adecuado."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_parser import BaseParser
from .configurable_parser import ConfigurableParser
from .error_parser import ErrorParser
from .event_parser import EventParser
from .metrics_parser import MetricsParser

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

PARSERS_ESTATICOS = [ErrorParser, MetricsParser, EventParser]

_MAPA_TIPOS: dict[str, type[BaseParser]] = {
    "errores": ErrorParser,
    "metricas": MetricsParser,
    "eventos": EventParser,
}


class ParserFactory:
    """Selecciona el parser adecuado para un fichero de log dado."""

    @staticmethod
    def detectar(ruta_fichero: str, db: "Session | None" = None) -> BaseParser:
        """Lee las primeras 20 líneas y elige el parser con mayor puntuación.

        Si se proporciona una sesión de BD, los parsers configurados en base
        de datos tienen prioridad sobre los parsers estáticos.

        Raises:
            ValueError: Si ningún parser reconoce el formato del fichero.
        """
        with open(ruta_fichero, "r", encoding="utf-8", errors="replace") as f:
            muestra = "".join([next(f, "") for _ in range(20)])

        lineas = muestra.splitlines()

        # --- Parsers de BD (prioridad alta) ---
        if db is not None:
            parser_bd = ParserFactory._mejor_parser_bd(lineas, db)
            if parser_bd is not None:
                logger.debug(
                    "Parser BD seleccionado para '%s': %s", ruta_fichero, parser_bd.nombre
                )
                return parser_bd

        # --- Parsers estáticos (fallback) ---
        puntuaciones: dict[type[BaseParser], int] = {
            P: sum(1 for linea in lineas if P().puede_parsear(linea))
            for P in PARSERS_ESTATICOS
        }
        mejor_clase = max(puntuaciones, key=lambda p: puntuaciones[p])
        if puntuaciones[mejor_clase] == 0:
            raise ValueError(
                f"No se reconoce el formato de '{ruta_fichero}'. "
                "Usa --tipo para especificar el parser manualmente."
            )
        return mejor_clase()

    @staticmethod
    def por_tipo(tipo: str) -> BaseParser:
        """Devuelve el parser estático correspondiente al tipo indicado.

        Args:
            tipo: Uno de 'errores', 'metricas', 'eventos'.

        Raises:
            ValueError: Si el tipo no está registrado.
        """
        if tipo not in _MAPA_TIPOS:
            tipos_validos = ", ".join(sorted(_MAPA_TIPOS))
            raise ValueError(
                f"Tipo de parser desconocido: '{tipo}'. "
                f"Valores válidos: {tipos_validos}."
            )
        return _MAPA_TIPOS[tipo]()

    @staticmethod
    def cargar_desde_db(db: "Session") -> list[ConfigurableParser]:
        """Carga todos los parsers activos definidos en la base de datos.

        Las relaciones (patrones, campos, fuentes) se cargan en la misma consulta
        para evitar N+1 queries.
        """
        from sqlalchemy.orm import joinedload
        from ..models.configuracion_parser import ConfiguracionParser

        configs = (
            db.query(ConfiguracionParser)
            .filter_by(activo=True)
            .options(
                joinedload(ConfiguracionParser.patrones),
                joinedload(ConfiguracionParser.campos),
                joinedload(ConfiguracionParser.fuentes),
            )
            .all()
        )
        return [ConfigurableParser(c) for c in configs]

    @staticmethod
    def _mejor_parser_bd(lineas: list[str], db: "Session") -> ConfigurableParser | None:
        """Devuelve el parser de BD con mayor puntuación, o None si ninguno reconoce."""
        parsers = ParserFactory.cargar_desde_db(db)
        if not parsers:
            return None

        puntuaciones = {
            p: sum(1 for linea in lineas if p.puede_parsear(linea))
            for p in parsers
        }
        mejor = max(puntuaciones, key=lambda p: puntuaciones[p])
        return mejor if puntuaciones[mejor] > 0 else None

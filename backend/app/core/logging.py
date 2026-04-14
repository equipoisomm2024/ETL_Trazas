"""Configuración del sistema de logging de la aplicación."""

import logging
import logging.handlers
from pathlib import Path

from .config import settings


def configurar_logging() -> None:
    """Inicializa el logger raíz con handlers de consola y fichero."""
    nivel = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formato = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(nivel)

    # Handler de consola
    handler_consola = logging.StreamHandler()
    handler_consola.setFormatter(formato)
    logger_raiz.addHandler(handler_consola)

    # Handler de fichero con rotación diaria
    ruta_log: Path = settings.LOG_FILE
    ruta_log.parent.mkdir(parents=True, exist_ok=True)

    handler_fichero = logging.handlers.TimedRotatingFileHandler(
        filename=ruta_log,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    handler_fichero.setFormatter(formato)
    logger_raiz.addHandler(handler_fichero)

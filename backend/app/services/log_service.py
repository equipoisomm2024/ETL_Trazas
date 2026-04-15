"""Servicio de persistencia: inserta registros de log en la tabla correspondiente."""

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from ..models.error import Error
from ..models.event import Evento
from ..models.metric import Metrica
from ..parsers.base_parser import ParsedRecord

logger = logging.getLogger(__name__)

# Mapa de tabla_destino → clase ORM
_MODELO_POR_TABLA: dict[str, type] = {
    "t_errores": Error,
    "t_metricas": Metrica,
    "t_eventos": Evento,
}


class LogService:
    """Encapsula la lógica de inserción masiva de registros en la base de datos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def insertar_batch(self, batch: Sequence[ParsedRecord]) -> int:
        """Inserta un lote de ParsedRecord en las tablas correspondientes.

        Los registros se agrupan por tabla_destino para minimizar el número
        de operaciones bulk_insert_mappings.

        Returns:
            Número de registros efectivamente insertados.
        """
        if not batch:
            return 0

        grupos: dict[str, list[dict]] = {}
        ahora = datetime.now(timezone.utc)

        for record in batch:
            tabla = record.tabla_destino
            if tabla not in _MODELO_POR_TABLA:
                logger.warning("Tabla desconocida '%s', registro ignorado.", tabla)
                continue
            datos = {**record.datos, "fecha_carga": ahora}
            grupos.setdefault(tabla, []).append(datos)

        insertados = 0
        for tabla, filas in grupos.items():
            modelo = _MODELO_POR_TABLA[tabla]
            self.db.bulk_insert_mappings(modelo, filas)
            insertados += len(filas)
            logger.debug("Insertados %d registros en %s.", len(filas), tabla)

        return insertados

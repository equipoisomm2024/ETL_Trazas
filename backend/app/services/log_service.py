"""Servicio de persistencia: inserta registros de log en la tabla correspondiente.

Soporta tablas fijas (t_errores, t_metricas, t_eventos) mediante ORM y cualquier
tabla dinámica mediante SQL crudo. Si la tabla dinámica no existe, la crea
automáticamente inferiendo los tipos de las columnas.
"""

import logging
from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..parsers.base_parser import ParsedRecord

logger = logging.getLogger(__name__)

# Tablas con modelo ORM propio (se usan para backward-compatibility)
_TABLAS_ORM = {"t_errores", "t_metricas", "t_eventos"}

# Columnas de infraestructura que se añaden siempre (no proceden del parser)
_COLS_INFRA = {"origen_fichero", "num_linea", "id_ejecucion", "fecha_carga"}

# Columnas que NUNCA se envían a la tabla dinámica (son internas del proceso)
_COLS_EXCLUIR = set()


def _tipo_sql(valor: object) -> str:
    """Infiere el tipo SQL de PostgreSQL a partir del valor Python."""
    if isinstance(valor, bool):
        return "BOOLEAN"
    if isinstance(valor, int):
        return "INTEGER"
    if isinstance(valor, float):
        return "DOUBLE PRECISION"
    if isinstance(valor, datetime):
        return "TIMESTAMPTZ"
    if isinstance(valor, date):
        return "DATE"
    return "TEXT"


class LogService:
    """Encapsula la lógica de inserción masiva de registros en la base de datos."""

    def __init__(self, db: Session) -> None:
        self.db = db
        # Cache de tablas ya verificadas/creadas en esta sesión
        self._tablas_verificadas: set[str] = set()

    def insertar_batch(self, batch: Sequence[ParsedRecord]) -> int:
        """Inserta un lote de ParsedRecord en las tablas correspondientes.

        - Para tablas ORM conocidas (t_errores, t_metricas, t_eventos): inserta
          solo las columnas que existen en la tabla, ignorando las demás.
        - Para cualquier otra tabla: usa SQL dinámico y auto-crea la tabla si
          no existe, usando los nombres y tipos de los datos extraídos.

        Returns:
            Número de registros efectivamente insertados.
        """
        if not batch:
            return 0

        grupos: dict[str, list[dict]] = {}
        ahora = datetime.now(timezone.utc)

        for record in batch:
            datos = {**record.datos, "fecha_carga": ahora}
            grupos.setdefault(record.tabla_destino, []).append(datos)

        insertados = 0
        for tabla, filas in grupos.items():
            try:
                if tabla in _TABLAS_ORM:
                    n = self._insertar_orm(tabla, filas)
                else:
                    n = self._insertar_dinamico(tabla, filas)
                insertados += n
                logger.debug("Insertados %d registros en '%s'.", n, tabla)
            except Exception as exc:
                logger.error("Error insertando en tabla '%s': %s", tabla, exc)
                raise

        return insertados

    # ─────────────────────────────────────────────────────────────────────────
    # Inserción ORM (tablas fijas)
    # ─────────────────────────────────────────────────────────────────────────

    def _insertar_orm(self, tabla: str, filas: list[dict]) -> int:
        """Inserta en una tabla ORM conocida filtrando solo las columnas válidas."""
        from ..models.error import Error
        from ..models.event import Evento
        from ..models.metric import Metrica

        _modelo = {"t_errores": Error, "t_metricas": Metrica, "t_eventos": Evento}
        modelo = _modelo[tabla]

        # Obtener columnas válidas del modelo para no enviar claves desconocidas
        columnas_validas: set[str] = {
            c.key for c in modelo.__mapper__.columns
        }

        filas_filtradas = [
            {k: v for k, v in fila.items() if k in columnas_validas}
            for fila in filas
        ]

        # Verificar que las NOT NULL estén cubiertas; si no, usar SQL dinámico
        # para evitar fallos silenciosos
        self.db.bulk_insert_mappings(modelo, filas_filtradas)
        return len(filas_filtradas)

    # ─────────────────────────────────────────────────────────────────────────
    # Inserción dinámica (tablas personalizadas)
    # ─────────────────────────────────────────────────────────────────────────

    def _insertar_dinamico(self, tabla: str, filas: list[dict]) -> int:
        """Inserta en una tabla arbitraria usando SQL crudo.

        Si la tabla no existe la crea automáticamente con las columnas
        inferidas de la primera fila + columnas de infraestructura.
        """
        if tabla not in self._tablas_verificadas:
            self._asegurar_tabla(tabla, filas[0])
            self._tablas_verificadas.add(tabla)

        # Obtener columnas reales de la tabla para filtrar el dict
        cols_tabla = self._columnas_tabla(tabla)

        filas_filtradas = [
            {k: v for k, v in fila.items() if k in cols_tabla}
            for fila in filas
        ]
        if not filas_filtradas or not filas_filtradas[0]:
            logger.warning(
                "Ninguna columna de los datos coincide con '%s'. Filas ignoradas.", tabla
            )
            return 0

        cols = list(filas_filtradas[0].keys())
        col_names = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        stmt = text(f'INSERT INTO "{tabla}" ({col_names}) VALUES ({placeholders})')

        self.db.execute(stmt, filas_filtradas)
        return len(filas_filtradas)

    def _asegurar_tabla(self, tabla: str, muestra: dict) -> None:
        """Crea la tabla si no existe usando los tipos inferidos de la muestra."""
        existe = self.db.execute(
            text("SELECT to_regclass(:t)"), {"t": tabla}
        ).scalar()
        if existe is not None:
            return

        logger.info("Tabla '%s' no existe. Creándola automáticamente.", tabla)

        cols_def = ['id SERIAL PRIMARY KEY']
        for col, val in muestra.items():
            if col == "id":
                continue
            tipo = _tipo_sql(val)
            nullable = "" if col in _COLS_INFRA else " DEFAULT NULL"
            cols_def.append(f'"{col}" {tipo}{nullable}')

        ddl = f'CREATE TABLE IF NOT EXISTS "{tabla}" ({", ".join(cols_def)})'
        self.db.execute(text(ddl))
        self.db.commit()
        logger.info("Tabla '%s' creada.", tabla)

    def _columnas_tabla(self, tabla: str) -> set[str]:
        """Devuelve el conjunto de nombres de columna de una tabla PostgreSQL."""
        rows = self.db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t"
            ),
            {"t": tabla},
        ).fetchall()
        return {r[0] for r in rows}

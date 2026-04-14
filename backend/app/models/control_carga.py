"""Modelo ORM para la tabla t_control_carga."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ControlCarga(Base):
    """Control incremental de procesamiento de ficheros de log.

    Registra el estado de cada ejecución por fichero, permitiendo
    reanudar el procesamiento desde la última línea leída.
    """

    __tablename__ = "t_control_carga"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_ejecucion: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ruta_fichero: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="EN_PROCESO"
    )  # EN_PROCESO | COMPLETADO | ERROR
    ultima_linea: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lineas_procesadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registros_insertados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ControlCarga id={self.id} fichero={self.ruta_fichero} "
            f"estado={self.estado} ultima_linea={self.ultima_linea}>"
        )

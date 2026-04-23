"""Modelo ORM para tareas de procesamiento programado."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


TIPOS_FUENTE = ("fuentes_bd", "directorio", "fichero")


class TareaScheduler(Base):
    """Define una tarea periódica de procesamiento de logs."""

    __tablename__ = "t_tarea_scheduler"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Planificación: expresión cron estándar (5 campos: min hora dom mes dow)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)

    # Qué procesar
    tipo_fuente: Mapped[str] = mapped_column(String(20), nullable=False, default="fuentes_bd")
    ruta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_parser: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("t_configuracion_parser.id", ondelete="SET NULL"), nullable=True
    )
    forzar_completo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ultima_ejecucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proxima_ejecucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    parser: Mapped["ConfiguracionParser | None"] = relationship(  # noqa: F821
        "ConfiguracionParser", foreign_keys=[id_parser]
    )

    def __repr__(self) -> str:
        return (
            f"<TareaScheduler id={self.id} nombre={self.nombre} "
            f"cron={self.cron_expression!r} activo={self.activo}>"
        )

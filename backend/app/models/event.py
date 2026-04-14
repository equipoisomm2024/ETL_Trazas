"""Modelo ORM para la tabla t_eventos."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Evento(Base):
    """Registro de evento de aplicación extraído de un fichero de log."""

    __tablename__ = "t_eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_hora: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tipo_evento: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    usuario: Mapped[str | None] = mapped_column(String(255), nullable=True)
    componente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origen_fichero: Mapped[str] = mapped_column(String(500), nullable=False)
    num_linea: Mapped[int] = mapped_column(Integer, nullable=False)
    id_ejecucion: Mapped[str] = mapped_column(String(36), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Evento id={self.id} tipo={self.tipo_evento}>"

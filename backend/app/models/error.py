"""Modelo ORM para la tabla t_errores."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Error(Base):
    """Registro de error extraído de un fichero de log."""

    __tablename__ = "t_errores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_hora: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nivel: Mapped[str] = mapped_column(String(20), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    componente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origen_fichero: Mapped[str] = mapped_column(String(500), nullable=False)
    num_linea: Mapped[int] = mapped_column(Integer, nullable=False)
    id_ejecucion: Mapped[str] = mapped_column(String(36), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Error id={self.id} nivel={self.nivel} fichero={self.origen_fichero}>"

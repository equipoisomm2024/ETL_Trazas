"""Modelo ORM para la tabla t_metricas."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Metrica(Base):
    """Registro de métrica numérica extraída de un fichero de log."""

    __tablename__ = "t_metricas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_hora: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nombre_metrica: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    unidad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    componente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origen_fichero: Mapped[str] = mapped_column(String(500), nullable=False)
    num_linea: Mapped[int] = mapped_column(Integer, nullable=False)
    id_ejecucion: Mapped[str] = mapped_column(String(36), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Metrica id={self.id} nombre={self.nombre_metrica} valor={self.valor}>"

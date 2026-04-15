"""Modelos ORM para la configuración dinámica de parsers."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ConfiguracionParser(Base):
    """Define un parser configurable: qué extraer, de dónde y a qué tabla."""

    __tablename__ = "t_configuracion_parser"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tabla_destino: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    patrones: Mapped[list["PatronExtraccion"]] = relationship(
        "PatronExtraccion",
        back_populates="parser",
        cascade="all, delete-orphan",
        order_by="PatronExtraccion.orden",
    )
    campos: Mapped[list["CampoExtraccion"]] = relationship(
        "CampoExtraccion",
        back_populates="parser",
        cascade="all, delete-orphan",
        order_by="CampoExtraccion.orden",
    )
    fuentes: Mapped[list["FuenteFichero"]] = relationship(
        "FuenteFichero",
        back_populates="parser",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ConfiguracionParser id={self.id} nombre={self.nombre} activo={self.activo}>"


class PatronExtraccion(Base):
    """Expresión regular de extracción. Un parser puede tener varios, probados en orden."""

    __tablename__ = "t_patron_extraccion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_parser: Mapped[int] = mapped_column(
        Integer, ForeignKey("t_configuracion_parser.id", ondelete="CASCADE"), nullable=False
    )
    expresion_regular: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parser: Mapped["ConfiguracionParser"] = relationship(
        "ConfiguracionParser", back_populates="patrones"
    )

    def __repr__(self) -> str:
        return f"<PatronExtraccion id={self.id} parser={self.id_parser} orden={self.orden}>"


class CampoExtraccion(Base):
    """Mapeo de un grupo regex a una columna de BD, con tipo de dato y opcionalidad."""

    __tablename__ = "t_campo_extraccion"

    TIPOS_VALIDOS = {"varchar", "text", "integer", "float", "datetime", "date", "boolean"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_parser: Mapped[int] = mapped_column(
        Integer, ForeignKey("t_configuracion_parser.id", ondelete="CASCADE"), nullable=False
    )
    nombre_grupo: Mapped[str] = mapped_column(String(100), nullable=False)
    campo_bd: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_dato: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    longitud: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opcional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valor_defecto: Mapped[str | None] = mapped_column(Text, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    parser: Mapped["ConfiguracionParser"] = relationship(
        "ConfiguracionParser", back_populates="campos"
    )

    def __repr__(self) -> str:
        return (
            f"<CampoExtraccion id={self.id} grupo={self.nombre_grupo} "
            f"→ {self.campo_bd} [{self.tipo_dato}]>"
        )


class FuenteFichero(Base):
    """Ruta o patrón glob de ficheros a procesar con un parser concreto."""

    __tablename__ = "t_fuente_fichero"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_parser: Mapped[int] = mapped_column(
        Integer, ForeignKey("t_configuracion_parser.id", ondelete="CASCADE"), nullable=False
    )
    ruta_patron: Mapped[str] = mapped_column(String(500), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parser: Mapped["ConfiguracionParser"] = relationship(
        "ConfiguracionParser", back_populates="fuentes"
    )

    def __repr__(self) -> str:
        return f"<FuenteFichero id={self.id} patron={self.ruta_patron} activo={self.activo}>"

"""Schemas Pydantic para configuración de parsers."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

TipoDato = Literal["varchar", "text", "integer", "float", "datetime", "date", "boolean"]


# ---------------------------------------------------------------------------
# PatronExtraccion
# ---------------------------------------------------------------------------

class PatronExtraccionCrear(BaseModel):
    """Datos necesarios para crear un patrón de extracción."""
    expresion_regular: str
    orden: int = 0
    activo: bool = True


class PatronExtraccionActualizar(BaseModel):
    """Campos opcionales para actualizar un patrón."""
    expresion_regular: str | None = None
    orden: int | None = None
    activo: bool | None = None


class PatronExtraccionSalida(BaseModel):
    """Representación de un patrón de extracción en respuestas API."""
    id: int
    id_parser: int
    expresion_regular: str
    orden: int
    activo: bool
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# CampoExtraccion
# ---------------------------------------------------------------------------

class CampoExtraccionCrear(BaseModel):
    """Datos necesarios para crear un campo de extracción."""
    nombre_grupo: str | None = None
    nombres_grupos_union: str | None = None
    expresion: str | None = None
    campo_bd: str
    tipo_dato: TipoDato = "text"
    longitud: int | None = None
    opcional: bool = False
    valor_defecto: str | None = None
    orden: int = 0

    @field_validator("longitud")
    @classmethod
    def longitud_solo_para_varchar(cls, v, info):
        tipo = info.data.get("tipo_dato")
        if v is not None and tipo != "varchar":
            raise ValueError("'longitud' solo aplica cuando tipo_dato es 'varchar'.")
        return v


class CampoExtraccionActualizar(BaseModel):
    """Campos opcionales para actualizar un campo de extracción."""
    nombre_grupo: str | None = None
    nombres_grupos_union: str | None = None
    expresion: str | None = None
    campo_bd: str | None = None
    tipo_dato: TipoDato | None = None
    longitud: int | None = None
    opcional: bool | None = None
    valor_defecto: str | None = None
    orden: int | None = None


class CampoExtraccionSalida(BaseModel):
    """Representación de un campo de extracción en respuestas API."""
    id: int
    id_parser: int
    nombre_grupo: str | None
    nombres_grupos_union: str | None
    expresion: str | None
    campo_bd: str
    tipo_dato: str
    longitud: int | None
    opcional: bool
    valor_defecto: str | None
    orden: int
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FuenteFichero
# ---------------------------------------------------------------------------

class FuenteFicheroCrear(BaseModel):
    """Datos necesarios para crear una fuente de fichero."""
    ruta_patron: str
    descripcion: str | None = None
    activo: bool = True


class FuenteFicheroActualizar(BaseModel):
    """Campos opcionales para actualizar una fuente de fichero."""
    ruta_patron: str | None = None
    descripcion: str | None = None
    activo: bool | None = None


class FuenteFicheroSalida(BaseModel):
    """Representación de una fuente de fichero en respuestas API."""
    id: int
    id_parser: int
    ruta_patron: str
    descripcion: str | None
    activo: bool
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ConfiguracionParser
# ---------------------------------------------------------------------------

class ConfiguracionParserCrear(BaseModel):
    """Datos para crear un parser completo con sus patrones, campos y fuentes."""
    nombre: str
    descripcion: str | None = None
    tabla_destino: str
    activo: bool = True
    separador_campos: str | None = " "
    filtro_where: str | None = None
    patrones: list[PatronExtraccionCrear] = []
    campos: list[CampoExtraccionCrear] = []
    fuentes: list[FuenteFicheroCrear] = []


class ConfiguracionParserActualizar(BaseModel):
    """Campos opcionales para actualizar un parser (PATCH — parcial)."""
    nombre: str | None = None
    descripcion: str | None = None
    tabla_destino: str | None = None
    activo: bool | None = None
    separador_campos: str | None = None
    filtro_where: str | None = None


class ConfiguracionParserReemplazar(ConfiguracionParserCrear):
    """Payload para PUT: reemplaza el parser completo incluyendo sus relaciones."""


class ConfiguracionParserSalida(BaseModel):
    """Representación completa de un parser en respuestas API."""
    id: int
    nombre: str
    descripcion: str | None
    tabla_destino: str
    activo: bool
    separador_campos: str | None
    filtro_where: str | None
    fecha_creacion: datetime
    fecha_modificacion: datetime
    patrones: list[PatronExtraccionSalida] = []
    campos: list[CampoExtraccionSalida] = []
    fuentes: list[FuenteFicheroSalida] = []
    model_config = ConfigDict(from_attributes=True)


class ConfiguracionParserResumen(BaseModel):
    """Versión resumida para listados (sin relaciones anidadas)."""
    id: int
    nombre: str
    descripcion: str | None
    tabla_destino: str
    activo: bool
    fecha_creacion: datetime
    fecha_modificacion: datetime
    num_patrones: int = 0
    num_campos: int = 0
    num_fuentes: int = 0
    model_config = ConfigDict(from_attributes=True)

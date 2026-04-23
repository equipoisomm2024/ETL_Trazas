"""Schemas Pydantic para tareas programadas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TipoFuente = Literal["fuentes_bd", "directorio", "fichero"]


class TareaSchedulerCrear(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = None
    cron_expression: str = Field(..., description="Expresión cron estándar de 5 campos")
    tipo_fuente: TipoFuente = "fuentes_bd"
    ruta: str | None = None
    id_parser: int | None = None
    forzar_completo: bool = False
    activo: bool = True

    @model_validator(mode="after")
    def ruta_requerida_si_no_bd(self) -> "TareaSchedulerCrear":
        if self.tipo_fuente in ("directorio", "fichero") and not self.ruta:
            raise ValueError(
                f"Se requiere 'ruta' cuando tipo_fuente es '{self.tipo_fuente}'."
            )
        return self


class TareaSchedulerActualizar(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    descripcion: str | None = None
    cron_expression: str | None = None
    tipo_fuente: TipoFuente | None = None
    ruta: str | None = None
    id_parser: int | None = None
    forzar_completo: bool | None = None
    activo: bool | None = None


class TareaSchedulerSalida(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    cron_expression: str
    tipo_fuente: str
    ruta: str | None
    id_parser: int | None
    forzar_completo: bool
    activo: bool
    ultima_ejecucion: datetime | None
    proxima_ejecucion: datetime | None
    fecha_creacion: datetime
    fecha_modificacion: datetime

    model_config = {"from_attributes": True}

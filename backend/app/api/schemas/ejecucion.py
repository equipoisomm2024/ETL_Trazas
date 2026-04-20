"""Schemas Pydantic para ejecuciones de procesamiento."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

EstadoEjecucion = Literal["EN_PROCESO", "COMPLETADO", "ERROR"]


class ControlCargaSalida(BaseModel):
    """Representación de una ejecución registrada en t_control_carga."""
    id: int
    id_ejecucion: str
    ruta_fichero: str
    fecha_inicio: datetime
    fecha_fin: datetime | None
    estado: str
    ultima_linea: int
    lineas_procesadas: int
    registros_insertados: int
    mensaje_error: str | None
    model_config = ConfigDict(from_attributes=True)


class ListaEjecucionesSalida(BaseModel):
    """Respuesta paginada de ejecuciones."""
    total: int
    limit: int
    offset: int
    items: list[ControlCargaSalida]


class ProcesarRequest(BaseModel):
    """Payload para lanzar un procesamiento desde la API.

    Exactamente una de las tres fuentes debe estar presente:
      - fichero: ruta a un fichero concreto
      - directorio: ruta a un directorio
      - usar_fuentes_bd: usar las fuentes configuradas en t_fuente_fichero
    """
    fichero: str | None = None
    directorio: str | None = None
    usar_fuentes_bd: bool = False
    forzar_completo: bool = False
    id_parser: int | None = None  # Parser explícito; si None se auto-detecta

    @model_validator(mode="after")
    def exactamente_una_fuente(self) -> "ProcesarRequest":
        fuentes = [
            self.fichero is not None,
            self.directorio is not None,
            self.usar_fuentes_bd,
        ]
        if sum(fuentes) != 1:
            raise ValueError(
                "Indica exactamente una fuente: 'fichero', 'directorio' o 'usar_fuentes_bd=true'."
            )
        return self


class ResultadoFichero(BaseModel):
    """Resultado del procesamiento de un único fichero."""
    fichero: str
    ok: bool
    parser: str | None = None
    id_ejecucion: str | None = None
    insertados: int | None = None
    lineas_procesadas: int | None = None
    error: str | None = None


class ProcesarResponse(BaseModel):
    """Respuesta agregada de un lanzamiento de procesamiento."""
    total_ficheros: int
    total_insertados: int
    total_errores: int
    resultados: list[ResultadoFichero]

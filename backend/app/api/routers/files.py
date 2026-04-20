"""Router para exploración del sistema de ficheros y previsualización de contenido."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/files", tags=["ficheros"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EntradaDirectorio(BaseModel):
    nombre: str
    ruta: str
    es_directorio: bool
    extension: Optional[str] = None


class ContenidoDirectorio(BaseModel):
    ruta_actual: str
    ruta_padre: Optional[str] = None
    entradas: List[EntradaDirectorio]


class PreviewRequest(BaseModel):
    ruta: str
    delimitador: str = " "
    num_lineas: int = 5


class CampoDetectado(BaseModel):
    posicion: int
    valor: str


class LineaPreview(BaseModel):
    numero: int
    contenido: str
    campos: List[CampoDetectado]


class PreviewResponse(BaseModel):
    ruta: str
    delimitador: str
    lineas: List[LineaPreview]
    num_campos: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/browse", response_model=ContenidoDirectorio)
def explorar_directorio(path: str = "/"):
    """Lista el contenido de un directorio del servidor."""
    ruta = Path(path).resolve()

    # Si se pasa un fichero, navegar al directorio padre
    if ruta.exists() and ruta.is_file():
        ruta = ruta.parent

    if not ruta.exists() or not ruta.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directorio no encontrado: '{path}'.",
        )

    entradas: List[EntradaDirectorio] = []
    try:
        for entrada in sorted(
            ruta.iterdir(),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        ):
            try:
                entradas.append(EntradaDirectorio(
                    nombre=entrada.name,
                    ruta=str(entrada.resolve()),
                    es_directorio=entrada.is_dir(),
                    extension=entrada.suffix.lower() if entrada.is_file() else None,
                ))
            except (PermissionError, OSError):
                continue
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permisos para leer '{path}'.",
        )

    padre = str(ruta.parent) if ruta.parent != ruta else None
    return ContenidoDirectorio(
        ruta_actual=str(ruta),
        ruta_padre=padre,
        entradas=entradas,
    )


@router.post("/preview", response_model=PreviewResponse)
def previsualizar_fichero(req: PreviewRequest):
    """Lee las primeras líneas de un fichero y detecta los campos según el delimitador."""
    ruta = Path(req.ruta)
    if not ruta.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el fichero '{req.ruta}'.",
        )

    lineas_resultado: List[LineaPreview] = []
    max_campos = 0

    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            for i, raw in enumerate(f):
                if i >= req.num_lineas:
                    break
                linea = raw.rstrip("\n\r")
                # Espacio: split por cualquier whitespace
                tokens = linea.split() if req.delimitador == " " else linea.split(req.delimitador)
                campos = [CampoDetectado(posicion=j, valor=t) for j, t in enumerate(tokens)]
                max_campos = max(max_campos, len(campos))
                lineas_resultado.append(LineaPreview(
                    numero=i + 1,
                    contenido=linea,
                    campos=campos,
                ))
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el fichero: {exc}",
        )

    return PreviewResponse(
        ruta=req.ruta,
        delimitador=req.delimitador,
        lineas=lineas_resultado,
        num_campos=max_campos,
    )

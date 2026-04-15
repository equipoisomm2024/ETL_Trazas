"""Router para consultar y lanzar ejecuciones de procesamiento."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models.control_carga import ControlCarga
from ...services.incremental_service import IncrementalService
from ...core.config import settings
from ..deps import get_db
from ..schemas.ejecucion import (
    ControlCargaSalida,
    ListaEjecucionesSalida,
    ProcesarRequest,
    ProcesarResponse,
    ResultadoFichero,
)

router = APIRouter(prefix="/ejecuciones", tags=["ejecuciones"])


# ---------------------------------------------------------------------------
# Consulta de ejecuciones
# ---------------------------------------------------------------------------

@router.get("/", response_model=ListaEjecucionesSalida)
def listar_ejecuciones(
    estado: str | None = None,
    fichero: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Lista ejecuciones registradas con filtros opcionales y paginación."""
    q = db.query(ControlCarga)
    if estado:
        q = q.filter(ControlCarga.estado == estado.upper())
    if fichero:
        q = q.filter(ControlCarga.ruta_fichero.ilike(f"%{fichero}%"))

    total = q.count()
    items = (
        q.order_by(ControlCarga.fecha_inicio.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ListaEjecucionesSalida(total=total, limit=limit, offset=offset, items=items)


@router.get("/{id_ejecucion}", response_model=ControlCargaSalida)
def obtener_ejecucion(id_ejecucion: str, db: Session = Depends(get_db)):
    """Devuelve el detalle de una ejecución por su UUID."""
    ejec = db.query(ControlCarga).filter_by(id_ejecucion=id_ejecucion).first()
    if ejec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejecución '{id_ejecucion}' no encontrada.",
        )
    return ejec


# ---------------------------------------------------------------------------
# Lanzar procesamiento
# ---------------------------------------------------------------------------

@router.post("/procesar", response_model=ProcesarResponse,
             status_code=status.HTTP_200_OK)
def procesar(payload: ProcesarRequest, db: Session = Depends(get_db)):
    """Lanza un procesamiento de logs y devuelve el resultado.

    Fuentes disponibles (exactamente una):
    - **fichero**: ruta absoluta a un fichero concreto.
    - **directorio**: ruta a un directorio (se procesan todos los ficheros con
      extensiones configuradas en LOG_EXTENSIONS).
    - **usar_fuentes_bd**: usa las fuentes configuradas en `t_fuente_fichero`.
    """
    svc = IncrementalService(db)
    resultados_raw: list[dict] = []

    if payload.fichero:
        ruta = Path(payload.fichero)
        if not ruta.is_file():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No existe el fichero '{payload.fichero}'.",
            )
        try:
            r = svc.procesar_fichero(str(ruta), forzar_completo=payload.forzar_completo)
            resultados_raw.append({"fichero": str(ruta), "ok": True, **r})
        except Exception as exc:
            resultados_raw.append({"fichero": str(ruta), "ok": False, "error": str(exc)})

    elif payload.directorio:
        ruta_dir = Path(payload.directorio)
        if not ruta_dir.is_dir():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No existe el directorio '{payload.directorio}'.",
            )
        extensiones = tuple(settings.extensiones_validas)
        resultados_raw = svc.procesar_directorio(
            str(ruta_dir),
            extensiones=extensiones,
            forzar_completo=payload.forzar_completo,
        )

    else:  # usar_fuentes_bd
        resultados_raw = svc.procesar_fuentes_configuradas(
            forzar_completo=payload.forzar_completo
        )

    return _construir_respuesta(resultados_raw)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _construir_respuesta(resultados_raw: list[dict]) -> ProcesarResponse:
    items = [
        ResultadoFichero(
            fichero=r["fichero"],
            ok=r["ok"],
            parser=r.get("parser"),
            id_ejecucion=r.get("id_ejecucion"),
            insertados=r.get("insertados"),
            lineas_procesadas=r.get("lineas_procesadas"),
            error=r.get("error"),
        )
        for r in resultados_raw
    ]
    return ProcesarResponse(
        total_ficheros=len(items),
        total_insertados=sum(r.insertados or 0 for r in items if r.ok),
        total_errores=sum(1 for r in items if not r.ok),
        resultados=items,
    )

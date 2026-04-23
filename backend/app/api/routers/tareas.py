"""Router para gestión de tareas programadas (APScheduler)."""

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models.tarea_scheduler import TareaScheduler
from ...scheduler import scheduler as sched
from ..deps import get_db
from ..schemas.scheduler import (
    TareaSchedulerActualizar,
    TareaSchedulerCrear,
    TareaSchedulerSalida,
)

router = APIRouter(prefix="/tareas", tags=["tareas"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enriquecer(tarea: TareaScheduler) -> TareaSchedulerSalida:
    """Añade proxima_ejecucion desde el scheduler en tiempo real."""
    next_run = sched.proxima_ejecucion(tarea.id)
    out = TareaSchedulerSalida.model_validate(tarea)
    out.proxima_ejecucion = next_run
    return out


def _validar_cron(expr: str) -> None:
    """Lanza HTTPException 422 si la expresión cron es inválida."""
    try:
        CronTrigger.from_crontab(expr, timezone="UTC")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Expresión cron inválida: {exc}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[TareaSchedulerSalida])
def listar_tareas(db: Session = Depends(get_db)):
    """Devuelve todas las tareas programadas."""
    tareas = db.query(TareaScheduler).order_by(TareaScheduler.nombre).all()
    return [_enriquecer(t) for t in tareas]


@router.post("/", response_model=TareaSchedulerSalida, status_code=status.HTTP_201_CREATED)
def crear_tarea(payload: TareaSchedulerCrear, db: Session = Depends(get_db)):
    """Crea una nueva tarea programada."""
    _validar_cron(payload.cron_expression)

    if db.query(TareaScheduler).filter_by(nombre=payload.nombre).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una tarea con el nombre '{payload.nombre}'.",
        )

    tarea = TareaScheduler(**payload.model_dump())
    db.add(tarea)
    db.commit()
    db.refresh(tarea)

    if tarea.activo:
        sched.registrar_tarea(tarea)

    return _enriquecer(tarea)


@router.get("/{id_tarea}", response_model=TareaSchedulerSalida)
def obtener_tarea(id_tarea: int, db: Session = Depends(get_db)):
    """Devuelve el detalle de una tarea."""
    tarea = db.get(TareaScheduler, id_tarea)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")
    return _enriquecer(tarea)


@router.patch("/{id_tarea}", response_model=TareaSchedulerSalida)
def actualizar_tarea(
    id_tarea: int, payload: TareaSchedulerActualizar, db: Session = Depends(get_db)
):
    """Actualiza parcialmente una tarea. Sincroniza el job con APScheduler."""
    tarea = db.get(TareaScheduler, id_tarea)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    cambios = payload.model_dump(exclude_none=True)

    if "cron_expression" in cambios:
        _validar_cron(cambios["cron_expression"])

    if "nombre" in cambios and cambios["nombre"] != tarea.nombre:
        if db.query(TareaScheduler).filter_by(nombre=cambios["nombre"]).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una tarea con el nombre '{cambios['nombre']}'.",
            )

    for campo, valor in cambios.items():
        setattr(tarea, campo, valor)

    db.commit()
    db.refresh(tarea)

    # Sincronizar con scheduler
    if tarea.activo:
        sched.registrar_tarea(tarea)
    else:
        sched.desregistrar_tarea(tarea.id)

    return _enriquecer(tarea)


@router.delete("/{id_tarea}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_tarea(id_tarea: int, db: Session = Depends(get_db)):
    """Elimina una tarea y cancela su job."""
    tarea = db.get(TareaScheduler, id_tarea)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    sched.desregistrar_tarea(tarea.id)
    db.delete(tarea)
    db.commit()


@router.post("/{id_tarea}/activar", response_model=TareaSchedulerSalida)
def activar_tarea(id_tarea: int, db: Session = Depends(get_db)):
    """Activa una tarea y registra su job en el scheduler."""
    tarea = db.get(TareaScheduler, id_tarea)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    tarea.activo = True
    db.commit()
    db.refresh(tarea)
    sched.registrar_tarea(tarea)
    return _enriquecer(tarea)


@router.post("/{id_tarea}/desactivar", response_model=TareaSchedulerSalida)
def desactivar_tarea(id_tarea: int, db: Session = Depends(get_db)):
    """Desactiva una tarea y cancela su job."""
    tarea = db.get(TareaScheduler, id_tarea)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    tarea.activo = False
    db.commit()
    db.refresh(tarea)
    sched.desregistrar_tarea(tarea.id)
    return _enriquecer(tarea)


@router.post("/{id_tarea}/ejecutar-ahora", response_model=dict)
def ejecutar_ahora(id_tarea: int, db: Session = Depends(get_db)):
    """Lanza la tarea de forma inmediata sin esperar al cron."""
    tarea = db.get(TareaScheduler, id_tarea)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    sched.ejecutar_ahora(tarea.id)
    return {"mensaje": f"Tarea '{tarea.nombre}' lanzada manualmente."}

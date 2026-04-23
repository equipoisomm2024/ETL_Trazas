"""Singleton de APScheduler para el procesamiento programado de tareas."""

import logging
from datetime import timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from ..models.tarea_scheduler import TareaScheduler
from .jobs import ejecutar_tarea, inicializar_session_factory

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ---------------------------------------------------------------------------
# Ciclo de vida
# ---------------------------------------------------------------------------

def iniciar(db: Session) -> None:
    """Arranca el scheduler y carga todas las tareas activas de BD."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler ya estaba en marcha.")
        return

    inicializar_session_factory()
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    logger.info("APScheduler iniciado.")

    # Cargar tareas activas desde BD
    tareas = db.query(TareaScheduler).filter_by(activo=True).all()
    for tarea in tareas:
        _registrar_job(tarea)
    logger.info("%d tarea(s) programada(s) cargadas desde BD.", len(tareas))


def detener() -> None:
    """Para el scheduler al apagar la aplicación."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler detenido.")
    _scheduler = None


# ---------------------------------------------------------------------------
# Gestión de jobs individuales
# ---------------------------------------------------------------------------

def _job_id(tarea_id: int) -> str:
    return f"tarea_{tarea_id}"


def _registrar_job(tarea: TareaScheduler) -> None:
    """Añade o reemplaza el job de una tarea en el scheduler."""
    if _scheduler is None:
        return
    try:
        trigger = CronTrigger.from_crontab(tarea.cron_expression, timezone="UTC")
        job = _scheduler.add_job(
            ejecutar_tarea,
            trigger=trigger,
            id=_job_id(tarea.id),
            args=[tarea.id],
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(
            "Job registrado: tarea '%s' (id=%d) cron=%r próxima=%s.",
            tarea.nombre, tarea.id, tarea.cron_expression, job.next_run_time,
        )
    except Exception as exc:
        logger.error("Error registrando job tarea %d: %s", tarea.id, exc)


def _desregistrar_job(tarea_id: int) -> None:
    """Elimina el job del scheduler si existe."""
    if _scheduler is None:
        return
    jid = _job_id(tarea_id)
    if _scheduler.get_job(jid):
        _scheduler.remove_job(jid)
        logger.info("Job eliminado: tarea id=%d.", tarea_id)


# ---------------------------------------------------------------------------
# API pública para el router
# ---------------------------------------------------------------------------

def registrar_tarea(tarea: TareaScheduler) -> None:
    """Registra (o reemplaza) el job de una tarea activa."""
    _registrar_job(tarea)


def desregistrar_tarea(tarea_id: int) -> None:
    """Elimina el job de una tarea del scheduler."""
    _desregistrar_job(tarea_id)


def proxima_ejecucion(tarea_id: int):
    """Devuelve el next_run_time del job o None si no existe."""
    if _scheduler is None:
        return None
    job = _scheduler.get_job(_job_id(tarea_id))
    if job is None:
        return None
    return job.next_run_time


def ejecutar_ahora(tarea_id: int) -> None:
    """Lanza el job de forma inmediata (ejecución puntual extra)."""
    if _scheduler is None:
        logger.error("Scheduler no iniciado, no se puede ejecutar tarea %d.", tarea_id)
        return
    _scheduler.add_job(
        ejecutar_tarea,
        trigger="date",
        id=f"manual_{tarea_id}",
        args=[tarea_id],
        replace_existing=True,
    )
    logger.info("Ejecución manual lanzada para tarea id=%d.", tarea_id)


def esta_activo() -> bool:
    return _scheduler is not None and _scheduler.running

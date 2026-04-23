"""Funciones de trabajo ejecutadas por APScheduler."""

import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from ..models.tarea_scheduler import TareaScheduler
from ..services.incremental_service import IncrementalService

logger = logging.getLogger(__name__)

# Fábrica de sesiones para los jobs (hilo propio, no puede reutilizar la sesión de FastAPI)
_SessionLocal: sessionmaker | None = None


def inicializar_session_factory() -> None:
    """Crea la fábrica de sesiones para los jobs del scheduler."""
    global _SessionLocal
    engine = create_engine(settings.DATABASE_URL)
    _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ejecutar_tarea(tarea_id: int) -> None:
    """Función ejecutada por APScheduler para cada tarea programada.

    Crea su propia sesión de BD (corre en hilo aparte), llama a IncrementalService
    y actualiza `ultima_ejecucion` en la tarea.
    """
    if _SessionLocal is None:
        logger.error("Session factory no inicializada. Tarea %d no ejecutada.", tarea_id)
        return

    with _SessionLocal() as db:
        tarea: TareaScheduler | None = db.get(TareaScheduler, tarea_id)
        if tarea is None:
            logger.warning("Tarea id=%d no encontrada en BD.", tarea_id)
            return

        logger.info(
            "Iniciando tarea programada '%s' (id=%d) tipo=%s.",
            tarea.nombre, tarea_id, tarea.tipo_fuente,
        )

        svc = IncrementalService(db)
        try:
            if tarea.tipo_fuente == "fuentes_bd":
                resultados = svc.procesar_fuentes_configuradas(
                    forzar_completo=tarea.forzar_completo
                )
            elif tarea.tipo_fuente == "directorio":
                if not tarea.ruta:
                    logger.error("Tarea '%s': tipo=directorio pero sin ruta.", tarea.nombre)
                    return
                from ..core.config import settings as cfg
                ext = tuple(cfg.extensiones_validas)
                resultados = svc.procesar_directorio(
                    tarea.ruta,
                    extensiones=ext,
                    forzar_completo=tarea.forzar_completo,
                )
            elif tarea.tipo_fuente == "fichero":
                if not tarea.ruta:
                    logger.error("Tarea '%s': tipo=fichero pero sin ruta.", tarea.nombre)
                    return
                resultado = svc.procesar_fichero(
                    tarea.ruta, forzar_completo=tarea.forzar_completo
                )
                resultados = [{"fichero": tarea.ruta, "ok": True, **resultado}]
            else:
                logger.error("Tarea '%s': tipo_fuente desconocido '%s'.", tarea.nombre, tarea.tipo_fuente)
                return

            ok = sum(1 for r in resultados if r.get("ok"))
            err = sum(1 for r in resultados if not r.get("ok"))
            logger.info(
                "Tarea '%s' completada: %d ficheros ok, %d errores.",
                tarea.nombre, ok, err,
            )
        except Exception as exc:
            logger.error("Tarea '%s' falló: %s", tarea.nombre, exc, exc_info=True)
        finally:
            tarea.ultima_ejecucion = datetime.now(timezone.utc)
            db.commit()

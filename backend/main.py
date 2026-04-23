"""Punto de entrada de la aplicación FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logging import configurar_logging
from app.api.routers import parsers, ejecuciones, files
from app.api.routers import tareas
from app.scheduler import scheduler as sched


def _crear_db_session():
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza al arrancar/parar la aplicación."""
    configurar_logging()
    db = _crear_db_session()
    try:
        sched.iniciar(db)
    finally:
        db.close()

    yield

    sched.detener()


app = FastAPI(
    title="LogPuller API",
    description="API REST para configurar parsers y gestionar la extracción incremental de logs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(parsers.router, prefix="/api")
app.include_router(ejecuciones.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(tareas.router, prefix="/api")


@app.get("/health", tags=["sistema"])
def health():
    """Comprobación de estado del servicio."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "scheduler": sched.esta_activo(),
    }

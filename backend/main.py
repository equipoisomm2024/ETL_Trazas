"""Punto de entrada de la aplicación FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configurar_logging
from app.api.routers import parsers, ejecuciones, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza al arrancar/parar la aplicación."""
    configurar_logging()
    yield


app = FastAPI(
    title="LogPuller API",
    description="API REST para configurar parsers y gestionar la extracción incremental de logs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(parsers.router, prefix="/api")
app.include_router(ejecuciones.router, prefix="/api")
app.include_router(files.router, prefix="/api")


@app.get("/health", tags=["sistema"])
def health():
    """Comprobación de estado del servicio."""
    return {"status": "ok", "version": "1.0.0"}

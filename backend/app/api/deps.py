"""Dependencias de inyección para los routers FastAPI."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from ..models.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependencia que provee una sesión de BD por request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

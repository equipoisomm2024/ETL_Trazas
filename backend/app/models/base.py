"""Base declarativa de SQLAlchemy y fábrica de sesiones."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..core.config import settings


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""
    pass


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Devuelve una sesión de base de datos. Usar como context manager."""
    return SessionLocal()

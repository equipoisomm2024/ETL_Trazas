"""Capa de servicios: lógica de negocio para procesamiento de logs."""

from .incremental_service import IncrementalService
from .log_service import LogService

__all__ = ["LogService", "IncrementalService"]

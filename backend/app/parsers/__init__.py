"""Módulo de parsers de log — patrón Strategy sobre BaseParser."""

from .base_parser import BaseParser, ParsedRecord
from .configurable_parser import ConfigurableParser
from .error_parser import ErrorParser
from .event_parser import EventParser
from .metrics_parser import MetricsParser
from .parser_factory import ParserFactory

__all__ = [
    "BaseParser",
    "ParsedRecord",
    "ConfigurableParser",
    "ErrorParser",
    "MetricsParser",
    "EventParser",
    "ParserFactory",
]

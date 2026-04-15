"""Tests unitarios para ParserFactory."""

import pytest

from app.parsers.error_parser import ErrorParser
from app.parsers.event_parser import EventParser
from app.parsers.metrics_parser import MetricsParser
from app.parsers.parser_factory import ParserFactory

_LOG_ERRORES = (
    "2026-04-13 08:45:10 ERROR core - fallo crítico\n"
    "2026-04-13 08:45:11 CRITICAL sys - disco lleno\n"
    "2026-04-13 08:45:12 WARN app - memoria alta\n"
)

_LOG_METRICAS = (
    "2026-04-13 08:45:10 METRIC cpu_usage=80.0 %\n"
    "2026-04-13 08:45:11 METRIC memory.used=1024.0 MB\n"
    "2026-04-13 08:45:12 METRICS disk.free=50.0 GB\n"
)

_LOG_EVENTOS = (
    "2026-04-13 08:45:10 EVENT user_login user=alice\n"
    "2026-04-13 08:45:11 EVENT order_created user=bob\n"
    "2026-04-13 08:45:12 EVENT session_expired\n"
)


@pytest.fixture
def log_errores(tmp_path):
    f = tmp_path / "errores.log"
    f.write_text(_LOG_ERRORES)
    return str(f)


@pytest.fixture
def log_metricas(tmp_path):
    f = tmp_path / "metricas.log"
    f.write_text(_LOG_METRICAS)
    return str(f)


@pytest.fixture
def log_eventos(tmp_path):
    f = tmp_path / "eventos.log"
    f.write_text(_LOG_EVENTOS)
    return str(f)


@pytest.fixture
def log_irreconocible(tmp_path):
    f = tmp_path / "raro.log"
    f.write_text("linea sin formato\notra linea\n")
    return str(f)


class TestDetectar:
    def test_detecta_error_parser(self, log_errores):
        parser = ParserFactory.detectar(log_errores)
        assert isinstance(parser, ErrorParser)

    def test_detecta_metrics_parser(self, log_metricas):
        parser = ParserFactory.detectar(log_metricas)
        assert isinstance(parser, MetricsParser)

    def test_detecta_event_parser(self, log_eventos):
        parser = ParserFactory.detectar(log_eventos)
        assert isinstance(parser, EventParser)

    def test_lanza_error_formato_desconocido(self, log_irreconocible):
        with pytest.raises(ValueError, match="No se reconoce el formato"):
            ParserFactory.detectar(log_irreconocible)


class TestPorTipo:
    def test_tipo_errores(self):
        assert isinstance(ParserFactory.por_tipo("errores"), ErrorParser)

    def test_tipo_metricas(self):
        assert isinstance(ParserFactory.por_tipo("metricas"), MetricsParser)

    def test_tipo_eventos(self):
        assert isinstance(ParserFactory.por_tipo("eventos"), EventParser)

    def test_tipo_desconocido_lanza_error(self):
        with pytest.raises(ValueError, match="Tipo de parser desconocido"):
            ParserFactory.por_tipo("desconocido")

    def test_mensaje_error_incluye_tipos_validos(self):
        with pytest.raises(ValueError) as exc_info:
            ParserFactory.por_tipo("xyz")
        mensaje = str(exc_info.value)
        assert "errores" in mensaje
        assert "metricas" in mensaje
        assert "eventos" in mensaje

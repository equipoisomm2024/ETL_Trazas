"""Tests unitarios para ErrorParser."""

import pytest

from app.parsers.error_parser import ErrorParser

LINEAS_VALIDAS = [
    "2026-04-13 08:45:12,345 [ERROR] com.app.Svc - NullPointerException: nulo",
    "2026-04-13 08:45:12 CRITICAL myapp - Disk space below 5%",
    "[2026-04-13T08:45:12] WARN - Memory usage at 95%",
    "2026-04-13 08:45:12 FATAL core.db - Connection pool exhausted",
    "2026-04-13 08:45:12,000 WARNING - Retry limit reached",
    "2026-04-13 08:45:12 ERROR - Simple error without component",
]

LINEAS_INVALIDAS = [
    "2026-04-13 08:45:12 INFO Starting server on port 8080",
    "2026-04-13 08:45:12 DEBUG Loading configuration file",
    "linea sin formato reconocible",
    "",
    "   ",
]

NIVELES_ACEPTADOS = {"ERROR", "WARN", "CRITICAL"}


@pytest.fixture
def parser():
    return ErrorParser()


class TestParsearLinea:
    def test_parsea_todas_las_lineas_validas(self, parser):
        for linea in LINEAS_VALIDAS:
            record = parser.parsear_linea(linea, 1, "test.log")
            assert record is not None, f"Debería parsear: {linea!r}"

    def test_tabla_destino_es_t_errores(self, parser):
        for linea in LINEAS_VALIDAS:
            record = parser.parsear_linea(linea, 1, "test.log")
            assert record.tabla_destino == "t_errores"

    def test_ignora_nivel_info(self, parser):
        linea = "2026-04-13 08:45:12 INFO Starting server on port 8080"
        assert parser.parsear_linea(linea, 1, "test.log") is None

    def test_ignora_nivel_debug(self, parser):
        linea = "2026-04-13 08:45:12 DEBUG Loading config"
        assert parser.parsear_linea(linea, 1, "test.log") is None

    def test_ignora_lineas_sin_formato(self, parser):
        for linea in LINEAS_INVALIDAS:
            assert parser.parsear_linea(linea, 1, "test.log") is None, (
                f"No debería parsear: {linea!r}"
            )

    def test_nivel_warning_normalizado_a_warn(self, parser):
        linea = "2026-04-13 08:45:12,000 WARNING - Retry limit reached"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["nivel"] == "WARN"

    def test_nivel_fatal_normalizado_a_error(self, parser):
        linea = "2026-04-13 08:45:12 FATAL core.db - Connection pool exhausted"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["nivel"] == "ERROR"

    def test_extrae_componente(self, parser):
        linea = "2026-04-13 08:45:12,345 [ERROR] com.app.Svc - NullPointerException"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["componente"] == "com.app.Svc"

    def test_componente_none_cuando_no_presente(self, parser):
        linea = "[2026-04-13T08:45:12] WARN - Memory usage at 95%"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["componente"] is None

    def test_extrae_mensaje(self, parser):
        linea = "2026-04-13 08:45:12 ERROR - Simple error without component"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["mensaje"] == "Simple error without component"

    def test_num_linea_en_record(self, parser):
        linea = "2026-04-13 08:45:12 ERROR - fallo"
        record = parser.parsear_linea(linea, 42, "test.log")
        assert record.num_linea == 42
        assert record.datos["num_linea"] == 42

    def test_origen_fichero_en_record(self, parser):
        linea = "2026-04-13 08:45:12 ERROR - fallo"
        record = parser.parsear_linea(linea, 1, "/var/logs/app.log")
        assert record.origen_fichero == "/var/logs/app.log"
        assert record.datos["origen_fichero"] == "/var/logs/app.log"

    def test_fecha_hora_parseada(self, parser):
        from datetime import datetime
        linea = "2026-04-13 08:45:12 ERROR - fallo"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert isinstance(record.datos["fecha_hora"], datetime)
        assert record.datos["fecha_hora"].year == 2026


class TestPuedeParsear:
    def test_reconoce_muestra_con_errores(self, parser):
        muestra = "\n".join(LINEAS_VALIDAS[:3])
        assert parser.puede_parsear(muestra) is True

    def test_no_reconoce_muestra_sin_errores(self, parser):
        muestra = "2026-04-13 08:45:12 INFO server started\nlinea normal\n"
        assert parser.puede_parsear(muestra) is False


class TestParsearFichero:
    def test_itera_solo_lineas_de_error(self, parser, tmp_log_file):
        contenido = (
            "2026-04-13 08:45:10 INFO startup\n"
            "2026-04-13 08:45:11 ERROR core - fallo\n"
            "2026-04-13 08:45:12 DEBUG tick\n"
            "2026-04-13 08:45:13 CRITICAL sys - disco lleno\n"
        )
        ruta = tmp_log_file(contenido)
        records = list(parser.parsear_fichero(ruta))
        assert len(records) == 2
        niveles = {r.datos["nivel"] for r in records}
        assert niveles == {"ERROR", "CRITICAL"}

    def test_desde_linea_omite_anteriores(self, parser, tmp_log_file):
        contenido = (
            "2026-04-13 08:45:11 ERROR core - error1\n"
            "2026-04-13 08:45:12 ERROR core - error2\n"
            "2026-04-13 08:45:13 ERROR core - error3\n"
        )
        ruta = tmp_log_file(contenido)
        records = list(parser.parsear_fichero(ruta, desde_linea=1))
        assert len(records) == 2
        assert records[0].datos["mensaje"] == "error2"

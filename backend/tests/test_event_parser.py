"""Tests unitarios para EventParser."""

import pytest

from app.parsers.event_parser import EventParser

LINEAS_VALIDAS = [
    "2026-04-13 08:45:12 EVENT user_login user=john.doe - Acceso autorizado",
    "2026-04-13 08:45:12,345 [EVENT] app_started",
    "2026-04-13 08:45:12 EVENT order_created user=client1 component=shop",
    "[2026-04-13T08:45:12] EVENT session_expired - Token caducado",
    "2026-04-13 08:45:12 EVENTS payment_processed user=alice",
]

LINEAS_INVALIDAS = [
    "2026-04-13 08:45:12 ERROR core - NullPointerException",
    "2026-04-13 08:45:12 INFO Starting server on port 8080",
    "linea sin formato reconocible",
    "",
]


@pytest.fixture
def parser():
    return EventParser()


class TestParsearLinea:
    def test_parsea_todas_las_lineas_validas(self, parser):
        for linea in LINEAS_VALIDAS:
            record = parser.parsear_linea(linea, 1, "test.log")
            assert record is not None, f"Debería parsear: {linea!r}"

    def test_tabla_destino_es_t_eventos(self, parser):
        for linea in LINEAS_VALIDAS:
            record = parser.parsear_linea(linea, 1, "test.log")
            assert record.tabla_destino == "t_eventos"

    def test_ignora_lineas_invalidas(self, parser):
        for linea in LINEAS_INVALIDAS:
            assert parser.parsear_linea(linea, 1, "test.log") is None, (
                f"No debería parsear: {linea!r}"
            )

    def test_extrae_tipo_evento(self, parser):
        linea = "2026-04-13 08:45:12 EVENT user_login user=john.doe - Acceso autorizado"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["tipo_evento"] == "user_login"

    def test_extrae_usuario(self, parser):
        linea = "2026-04-13 08:45:12 EVENT user_login user=john.doe - Acceso autorizado"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["usuario"] == "john.doe"

    def test_usuario_none_cuando_no_presente(self, parser):
        linea = "2026-04-13 08:45:12,345 [EVENT] app_started"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["usuario"] is None

    def test_extrae_componente(self, parser):
        linea = "2026-04-13 08:45:12 EVENT order_created user=client1 component=shop"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["componente"] == "shop"

    def test_descripcion_no_vacia(self, parser):
        linea = "2026-04-13 08:45:12 EVENT user_login user=john.doe - Acceso autorizado"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["descripcion"]

    def test_num_linea_en_record(self, parser):
        linea = "2026-04-13 08:45:12 EVENT ping"
        record = parser.parsear_linea(linea, 15, "test.log")
        assert record is not None
        assert record.num_linea == 15

    def test_fecha_hora_parseada(self, parser):
        from datetime import datetime
        linea = "2026-04-13 08:45:12 EVENT user_login"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record is not None
        assert isinstance(record.datos["fecha_hora"], datetime)


class TestPuedeParsear:
    def test_reconoce_muestra_con_eventos(self, parser):
        muestra = "\n".join(LINEAS_VALIDAS[:3])
        assert parser.puede_parsear(muestra) is True

    def test_no_reconoce_muestra_de_errores(self, parser):
        muestra = (
            "2026-04-13 08:45:12 ERROR core - fallo\n"
            "2026-04-13 08:45:13 INFO server started\n"
        )
        assert parser.puede_parsear(muestra) is False


class TestParsearFichero:
    def test_itera_solo_lineas_de_evento(self, parser, tmp_log_file):
        contenido = (
            "2026-04-13 08:45:10 INFO startup\n"
            "2026-04-13 08:45:11 EVENT user_login user=alice\n"
            "2026-04-13 08:45:12 ERROR core - fallo\n"
            "2026-04-13 08:45:13 EVENT user_logout user=alice\n"
        )
        ruta = tmp_log_file(contenido)
        records = list(parser.parsear_fichero(ruta))
        assert len(records) == 2
        tipos = {r.datos["tipo_evento"] for r in records}
        assert tipos == {"user_login", "user_logout"}

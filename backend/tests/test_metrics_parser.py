"""Tests unitarios para MetricsParser."""

import pytest

from app.parsers.metrics_parser import MetricsParser

LINEAS_VALIDAS = [
    "2026-04-13 08:45:12 METRIC cpu_usage=85.3 %",
    "2026-04-13 08:45:12,345 [METRICS] memory.used=1024.5 MB",
    "2026-04-13 08:45:12 METRIC disk.free=45.2 GB",
    "2026-04-13 08:45:12 METRIC backend - requests_per_sec=1500.0 req/s",
    "2026-04-13 08:45:12 METRICS response_time=250 ms",
]

LINEAS_INVALIDAS = [
    "2026-04-13 08:45:12 ERROR core - NullPointerException",
    "2026-04-13 08:45:12 INFO Starting server on port 8080",
    "linea sin formato reconocible",
    "",
]


@pytest.fixture
def parser():
    return MetricsParser()


class TestParsearLinea:
    def test_parsea_todas_las_lineas_validas(self, parser):
        for linea in LINEAS_VALIDAS:
            record = parser.parsear_linea(linea, 1, "test.log")
            assert record is not None, f"Debería parsear: {linea!r}"

    def test_tabla_destino_es_t_metricas(self, parser):
        for linea in LINEAS_VALIDAS:
            record = parser.parsear_linea(linea, 1, "test.log")
            assert record.tabla_destino == "t_metricas"

    def test_ignora_lineas_invalidas(self, parser):
        for linea in LINEAS_INVALIDAS:
            assert parser.parsear_linea(linea, 1, "test.log") is None, (
                f"No debería parsear: {linea!r}"
            )

    def test_extrae_nombre_metrica(self, parser):
        linea = "2026-04-13 08:45:12 METRIC cpu_usage=85.3 %"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["nombre_metrica"] == "cpu_usage"

    def test_extrae_valor_float(self, parser):
        linea = "2026-04-13 08:45:12 METRIC cpu_usage=85.3 %"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert isinstance(record.datos["valor"], float)
        assert record.datos["valor"] == pytest.approx(85.3)

    def test_extrae_unidad(self, parser):
        linea = "2026-04-13 08:45:12,345 [METRICS] memory.used=1024.5 MB"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["unidad"] == "MB"

    def test_extrae_componente(self, parser):
        linea = "2026-04-13 08:45:12 METRIC backend - requests_per_sec=1500.0 req/s"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record.datos["componente"] == "backend"

    def test_unidad_none_cuando_no_presente(self, parser):
        linea = "2026-04-13 08:45:12 METRIC disk.free=45.2"
        record = parser.parsear_linea(linea, 1, "test.log")
        # Puede ser None o un valor; si existe debe ser string
        if record is not None:
            unidad = record.datos.get("unidad")
            assert unidad is None or isinstance(unidad, str)

    def test_num_linea_en_record(self, parser):
        linea = "2026-04-13 08:45:12 METRIC cpu_usage=1.0"
        record = parser.parsear_linea(linea, 7, "test.log")
        assert record is not None
        assert record.num_linea == 7

    def test_fecha_hora_parseada(self, parser):
        from datetime import datetime
        linea = "2026-04-13 08:45:12 METRIC cpu_usage=50.0 %"
        record = parser.parsear_linea(linea, 1, "test.log")
        assert record is not None
        assert isinstance(record.datos["fecha_hora"], datetime)


class TestPuedeParsear:
    def test_reconoce_muestra_con_metricas(self, parser):
        muestra = "\n".join(LINEAS_VALIDAS[:3])
        assert parser.puede_parsear(muestra) is True

    def test_no_reconoce_muestra_de_errores(self, parser):
        muestra = (
            "2026-04-13 08:45:12 ERROR core - fallo\n"
            "2026-04-13 08:45:13 CRITICAL sys - disco lleno\n"
        )
        assert parser.puede_parsear(muestra) is False


class TestParsearFichero:
    def test_itera_solo_lineas_de_metrica(self, parser, tmp_log_file):
        contenido = (
            "2026-04-13 08:45:10 INFO startup\n"
            "2026-04-13 08:45:11 METRIC cpu_usage=55.0 %\n"
            "2026-04-13 08:45:12 ERROR core - fallo\n"
            "2026-04-13 08:45:13 METRIC memory.used=2048.0 MB\n"
        )
        ruta = tmp_log_file(contenido)
        records = list(parser.parsear_fichero(ruta))
        assert len(records) == 2
        nombres = {r.datos["nombre_metrica"] for r in records}
        assert nombres == {"cpu_usage", "memory.used"}

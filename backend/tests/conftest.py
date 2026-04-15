"""Fixtures compartidas para los tests de LogPuller."""

import os
import tempfile

import pytest

# Asegurar que la variable de entorno mínima existe antes de importar módulos
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://logpuller:password@localhost:5432/logpuller"
)


@pytest.fixture
def tmp_log_file(tmp_path):
    """Devuelve una función para crear ficheros de log temporales."""

    def _crear(contenido: str, nombre: str = "test.log"):
        ruta = tmp_path / nombre
        ruta.write_text(contenido, encoding="utf-8")
        return str(ruta)

    return _crear

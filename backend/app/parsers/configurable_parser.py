"""Parser configurable desde base de datos."""

import logging
import re
from datetime import date, datetime
from typing import Optional

from .base_parser import BaseParser, ParsedRecord
from .qlik_filter import QlikWhereEvaluator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conversores de tipo: cadena extraída por regex → tipo Python correcto
# ---------------------------------------------------------------------------

def _a_boolean(valor: str) -> bool:
    return valor.strip().lower() in {"true", "1", "yes", "si", "sí"}


def _a_date(valor: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(valor.strip(), fmt).date()
        except ValueError:
            continue
    return None


_CONVERSORES: dict[str, callable] = {
    "varchar":  str,
    "text":     str,
    "integer":  int,
    "float":    float,
    "datetime": None,   # usa _parse_dt de BaseParser
    "date":     _a_date,
    "boolean":  _a_boolean,
}


class ConfigurableParser(BaseParser):
    """Parser cuya lógica de extracción está definida en la base de datos.

    Recibe los objetos ORM ya cargados (sin necesitar acceso a BD en tiempo
    de parseo) para que sea testeable de forma aislada.
    """

    def __init__(self, config) -> None:
        """
        Args:
            config: instancia de ConfiguracionParser con relaciones cargadas
                    (patrones, campos, fuentes).
        """
        self._config = config
        self._nombre = config.nombre
        self._tabla_destino = config.tabla_destino
        self._separador = getattr(config, "separador_campos", None) or " "
        self._patrones_compilados = self._compilar_patrones(config.patrones)
        self._campos = sorted(
            [c for c in config.campos],
            key=lambda c: c.orden,
        )
        filtro_expr = getattr(config, "filtro_where", None) or ""
        self._filtro = QlikWhereEvaluator(filtro_expr, self._separador)

    # ------------------------------------------------------------------
    # Interfaz BaseParser
    # ------------------------------------------------------------------

    def puede_parsear(self, muestra: str) -> bool:
        """Devuelve True si algún patrón activo reconoce al menos una línea de la muestra."""
        for linea in muestra.splitlines():
            for patron in self._patrones_compilados:
                if patron.search(linea):
                    return True
        return False

    def parsear_linea(
        self, linea: str, num_linea: int, origen: str
    ) -> Optional[ParsedRecord]:
        """Aplica el filtro WHERE, luego los patrones en orden, y mapea campos a BD."""
        if not self._filtro.matches(linea):
            return None
        for patron in self._patrones_compilados:
            m = patron.match(linea)
            if not m:
                continue
            datos = self._mapear_campos(m.groupdict(), origen, num_linea)
            if datos is None:
                continue
            return ParsedRecord(
                tabla_destino=self._tabla_destino,
                datos=datos,
                num_linea=num_linea,
                origen_fichero=origen,
            )
        return None

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _compilar_patrones(self, patrones_orm) -> list[re.Pattern]:
        """Compila las expresiones regulares activas, ordenadas por 'orden'."""
        compilados = []
        for p in sorted(patrones_orm, key=lambda x: x.orden):
            if not p.activo:
                continue
            try:
                compilados.append(re.compile(p.expresion_regular, re.IGNORECASE))
            except re.error as exc:
                logger.error(
                    "Parser '%s': expresión regex inválida (id=%d): %s",
                    self._nombre, p.id, exc,
                )
        return compilados

    def _mapear_campos(
        self, grupos: dict[str, str | None], origen: str, num_linea: int
    ) -> Optional[dict]:
        """Convierte los grupos capturados a un dict listo para inserción.

        Devuelve None si algún campo obligatorio no tiene valor.
        """
        datos: dict = {
            "origen_fichero": origen,
            "num_linea": num_linea,
        }

        for campo in self._campos:
            # Unión no contigua: concatenar varios grupos de captura
            nombres_union = getattr(campo, "nombres_grupos_union", None)
            if nombres_union:
                fragmentos = [
                    grupos.get(g, "") or ""
                    for g in nombres_union.split(",")
                ]
                valor_raw = " ".join(f for f in fragmentos if f.strip()) or None
            else:
                valor_raw = grupos.get(campo.nombre_grupo)

            if valor_raw is None or valor_raw.strip() == "":
                if campo.opcional:
                    datos[campo.campo_bd] = self._convertir(
                        campo.valor_defecto, campo.tipo_dato
                    ) if campo.valor_defecto is not None else None
                    continue
                else:
                    logger.debug(
                        "Parser '%s': campo obligatorio '%s' sin valor en línea %d.",
                        self._nombre, campo.nombre_grupo, num_linea,
                    )
                    return None

            datos[campo.campo_bd] = self._convertir(valor_raw, campo.tipo_dato)

        return datos

    def _convertir(self, valor: str | None, tipo: str) -> object:
        """Convierte una cadena al tipo Python correspondiente al tipo_dato definido."""
        if valor is None:
            return None
        conversor = _CONVERSORES.get(tipo)
        if conversor is None:
            # datetime usa el método heredado de BaseParser
            return self._parse_dt(valor)
        try:
            return conversor(valor.strip())
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Parser '%s': no se pudo convertir '%s' a tipo '%s': %s",
                self._nombre, valor, tipo, exc,
            )
            return valor  # devuelve la cadena original como fallback

    # ------------------------------------------------------------------
    # Propiedades de conveniencia
    # ------------------------------------------------------------------

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tabla_destino(self) -> str:
        return self._tabla_destino

    @property
    def fuentes_activas(self) -> list[str]:
        """Devuelve los patrones glob de fuentes activas."""
        return [f.ruta_patron for f in self._config.fuentes if f.activo]

    def __repr__(self) -> str:
        return f"<ConfigurableParser nombre={self._nombre} tabla={self._tabla_destino}>"

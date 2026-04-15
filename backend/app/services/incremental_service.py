"""Orquestador del procesamiento incremental de ficheros de log."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.control_carga import ControlCarga
from ..parsers.parser_factory import ParserFactory
from .log_service import LogService

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class IncrementalService:
    """Orquesta la detección, parseo e inserción incremental de ficheros de log.

    Para cada fichero determina el punto de inicio (última línea procesada)
    y delega la escritura en base de datos a LogService en lotes de BATCH_SIZE.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.log_service = LogService(db)

    def procesar_fichero(
        self,
        ruta: str,
        forzar_completo: bool = False,
        parser=None,
    ) -> dict:
        """Procesa un fichero de log de forma incremental.

        Crea un registro EN_PROCESO en t_control_carga al inicio y lo actualiza
        a COMPLETADO o ERROR al finalizar.

        Args:
            ruta: Ruta absoluta al fichero de log.
            forzar_completo: Si True, ignora el control incremental y reprocesa
                             el fichero desde el principio.
            parser: Parser a usar. Si None, se detecta automáticamente (con BD).

        Returns:
            Diccionario con id_ejecucion, insertados y lineas_procesadas.
        """
        id_ejec = str(uuid.uuid4())
        ctrl = ControlCarga(
            id_ejecucion=id_ejec,
            ruta_fichero=ruta,
            fecha_inicio=datetime.now(timezone.utc),
            estado="EN_PROCESO",
            lineas_procesadas=0,
            registros_insertados=0,
            ultima_linea=0,
        )
        self.db.add(ctrl)
        self.db.commit()
        logger.info("Iniciando procesamiento de '%s' (id=%s).", ruta, id_ejec)

        try:
            desde = 0 if forzar_completo else self._ultima_linea_procesada(ruta)
            if parser is None:
                parser = ParserFactory.detectar(ruta, db=self.db)
            logger.info(
                "Parser seleccionado: %s. Procesando desde línea %d.",
                type(parser).__name__,
                desde,
            )

            batch, insertados, lineas = [], 0, 0

            for record in parser.parsear_fichero(ruta, desde_linea=desde):
                record.datos["id_ejecucion"] = id_ejec
                batch.append(record)
                lineas += 1
                if len(batch) >= BATCH_SIZE:
                    insertados += self.log_service.insertar_batch(batch)
                    self.db.commit()
                    batch = []

            if batch:
                insertados += self.log_service.insertar_batch(batch)
                self.db.commit()

            ctrl.estado = "COMPLETADO"
            ctrl.ultima_linea = desde + lineas
            ctrl.lineas_procesadas = lineas
            ctrl.registros_insertados = insertados
            logger.info(
                "Fichero '%s' completado: %d líneas procesadas, %d registros insertados.",
                ruta,
                lineas,
                insertados,
            )

        except Exception as exc:
            ctrl.estado = "ERROR"
            ctrl.mensaje_error = str(exc)
            logger.error("Error procesando '%s': %s", ruta, exc, exc_info=True)
            raise

        finally:
            ctrl.fecha_fin = datetime.now(timezone.utc)
            self.db.commit()

        return {
            "id_ejecucion": id_ejec,
            "insertados": insertados,
            "lineas_procesadas": lineas,
        }

    def procesar_directorio(
        self,
        directorio: str,
        extensiones: tuple[str, ...] = (".log", ".txt", ".out"),
        forzar_completo: bool = False,
    ) -> list[dict]:
        """Procesa todos los ficheros de log de un directorio.

        Los errores en ficheros individuales no detienen el procesamiento
        del resto: se registran y se continúa con el siguiente.

        Returns:
            Lista de resultados por fichero, incluyendo los que fallaron.
        """
        ruta_dir = Path(directorio)
        ficheros = sorted(
            f for f in ruta_dir.iterdir()
            if f.is_file() and f.suffix.lower() in extensiones
        )

        if not ficheros:
            logger.warning("No se encontraron ficheros de log en '%s'.", directorio)
            return []

        resultados = []
        for fichero in ficheros:
            try:
                resultado = self.procesar_fichero(
                    str(fichero), forzar_completo=forzar_completo
                )
                resultados.append({"fichero": str(fichero), "ok": True, **resultado})
            except Exception as exc:
                resultados.append({
                    "fichero": str(fichero),
                    "ok": False,
                    "error": str(exc),
                })

        return resultados

    def _ultima_linea_procesada(self, ruta: str) -> int:
        """Devuelve la última línea procesada con éxito para el fichero dado."""
        ultimo = (
            self.db.query(ControlCarga)
            .filter_by(ruta_fichero=ruta, estado="COMPLETADO")
            .order_by(ControlCarga.fecha_fin.desc())
            .first()
        )
        return ultimo.ultima_linea if ultimo else 0

    def procesar_fuentes_configuradas(
        self, forzar_completo: bool = False
    ) -> list[dict]:
        """Procesa todas las fuentes activas definidas en t_fuente_fichero.

        Para cada parser activo en BD expande los patrones glob de sus fuentes
        y procesa cada fichero encontrado con ese parser concreto.

        Los errores en ficheros individuales no detienen el procesamiento del resto.

        Returns:
            Lista de resultados por fichero (ok/error, insertados, etc.).
        """
        import glob as glob_module

        parsers = ParserFactory.cargar_desde_db(self.db)
        if not parsers:
            logger.warning("No hay parsers configurados en BD.")
            return []

        resultados = []
        for parser in parsers:
            fuentes = parser.fuentes_activas
            if not fuentes:
                logger.info("Parser '%s' sin fuentes activas, omitido.", parser.nombre)
                continue

            for patron in fuentes:
                ficheros = sorted(glob_module.glob(patron, recursive=True))
                if not ficheros:
                    logger.warning(
                        "Parser '%s': el patrón '%s' no coincide con ningún fichero.",
                        parser.nombre, patron,
                    )
                for ruta in ficheros:
                    if not Path(ruta).is_file():
                        continue
                    try:
                        resultado = self.procesar_fichero(
                            ruta, forzar_completo=forzar_completo, parser=parser
                        )
                        resultados.append({
                            "fichero": ruta,
                            "parser": parser.nombre,
                            "ok": True,
                            **resultado,
                        })
                    except Exception as exc:
                        resultados.append({
                            "fichero": ruta,
                            "parser": parser.nombre,
                            "ok": False,
                            "error": str(exc),
                        })

        return resultados

    def estado_ejecuciones(self, limite: int = 20) -> list[ControlCarga]:
        """Devuelve las últimas ejecuciones registradas, ordenadas por fecha de inicio."""
        return (
            self.db.query(ControlCarga)
            .order_by(ControlCarga.fecha_inicio.desc())
            .limit(limite)
            .all()
        )

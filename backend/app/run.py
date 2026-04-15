"""Punto de entrada CLI del sistema LogPuller.

Uso:
    python -m app.run [opciones]

Ejemplos:
    python -m app.run --dir /var/logs/app
    python -m app.run --file /var/logs/app.log
    python -m app.run --file /var/logs/app.log --dry-run
    python -m app.run --dir /var/logs --force-full
    python -m app.run --status
"""

import argparse
import logging
import sys
from pathlib import Path

from .core.config import settings
from .core.logging import configurar_logging


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.run",
        description="LogPuller — extracción incremental de logs a PostgreSQL.",
    )
    origen = p.add_mutually_exclusive_group()
    origen.add_argument(
        "--file",
        metavar="RUTA",
        help="Procesar un único fichero de log.",
    )
    origen.add_argument(
        "--dir",
        metavar="DIRECTORIO",
        help="Procesar todos los logs de un directorio (por defecto: LOG_DIR de .env).",
    )
    origen.add_argument(
        "--status",
        action="store_true",
        help="Mostrar las últimas ejecuciones registradas y salir.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parsear sin insertar registros en la base de datos.",
    )
    p.add_argument(
        "--force-full",
        action="store_true",
        help="Ignorar el control incremental y reprocesar el fichero completo.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=20,
        metavar="N",
        help="Número de ejecuciones a mostrar con --status (por defecto: 20).",
    )
    return p


def _cmd_status(limit: int) -> None:
    """Muestra las últimas ejecuciones registradas en t_control_carga."""
    from .models.base import get_session
    from .services.incremental_service import IncrementalService

    with get_session() as db:
        svc = IncrementalService(db)
        filas = svc.estado_ejecuciones(limite=limit)

    if not filas:
        print("No hay ejecuciones registradas.")
        return

    ancho = 50
    print(f"\n{'FICHERO':<{ancho}}  {'ESTADO':<12}  {'LÍNEAS':>7}  {'INSERTOS':>9}  INICIO")
    print("-" * (ancho + 50))
    for f in filas:
        fichero = str(f.ruta_fichero)
        if len(fichero) > ancho:
            fichero = "…" + fichero[-(ancho - 1):]
        inicio = f.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S") if f.fecha_inicio else "-"
        print(
            f"{fichero:<{ancho}}  {f.estado:<12}  {f.lineas_procesadas:>7}  "
            f"{f.registros_insertados:>9}  {inicio}"
        )
    print()


def _cmd_dry_run(ruta: str) -> None:
    """Parsea un fichero e imprime los registros sin tocar la BD."""
    from .parsers.parser_factory import ParserFactory

    parser = ParserFactory.detectar(ruta)
    tipo = type(parser).__name__
    print(f"Parser seleccionado: {tipo}")
    print(f"Fichero: {ruta}\n")

    total = 0
    for record in parser.parsear_fichero(ruta):
        total += 1
        datos = record.datos
        print(
            f"  [{record.num_linea:>6}] {record.tabla_destino}  "
            + "  ".join(f"{k}={v!r}" for k, v in datos.items() if k != "id_ejecucion")
        )

    print(f"\nTotal registros parseados: {total}  (dry-run: no se ha insertado nada)")


def _cmd_procesar_fichero(ruta: str, forzar_completo: bool) -> None:
    """Procesa un único fichero e inserta en BD."""
    from .models.base import get_session
    from .services.incremental_service import IncrementalService

    with get_session() as db:
        svc = IncrementalService(db)
        resultado = svc.procesar_fichero(ruta, forzar_completo=forzar_completo)

    print(
        f"Completado — id={resultado['id_ejecucion']}  "
        f"líneas={resultado['lineas_procesadas']}  "
        f"insertados={resultado['insertados']}"
    )


def _cmd_procesar_directorio(directorio: str, forzar_completo: bool) -> None:
    """Procesa todos los logs de un directorio e inserta en BD."""
    from .models.base import get_session
    from .services.incremental_service import IncrementalService

    extensiones = tuple(settings.extensiones_validas)

    with get_session() as db:
        svc = IncrementalService(db)
        resultados = svc.procesar_directorio(
            directorio, extensiones=extensiones, forzar_completo=forzar_completo
        )

    if not resultados:
        print("No se encontraron ficheros de log.")
        return

    total_insertados = 0
    errores = 0
    for r in resultados:
        if r["ok"]:
            total_insertados += r.get("insertados", 0)
            print(f"  OK  {r['fichero']}  insertados={r.get('insertados', 0)}")
        else:
            errores += 1
            print(f"  ERR {r['fichero']}  error={r['error']}")

    print(f"\nResumen: {len(resultados)} ficheros  total insertados={total_insertados}  errores={errores}")


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal. Devuelve código de salida."""
    configurar_logging()
    logger = logging.getLogger(__name__)

    args = _build_parser().parse_args(argv)

    try:
        if args.status:
            _cmd_status(args.limit)
            return 0

        if args.file:
            ruta = Path(args.file)
            if not ruta.is_file():
                print(f"Error: no existe el fichero '{ruta}'.", file=sys.stderr)
                return 1
            if args.dry_run:
                _cmd_dry_run(str(ruta))
            else:
                _cmd_procesar_fichero(str(ruta), forzar_completo=args.force_full)
            return 0

        # --dir o directorio por defecto
        directorio = Path(args.dir) if args.dir else settings.LOG_DIR
        if not directorio.is_dir():
            print(f"Error: no existe el directorio '{directorio}'.", file=sys.stderr)
            return 1

        if args.dry_run:
            # dry-run sobre directorio: iterar cada fichero
            extensiones = tuple(settings.extensiones_validas)
            ficheros = sorted(
                f for f in directorio.iterdir()
                if f.is_file() and f.suffix.lower() in extensiones
            )
            for fichero in ficheros:
                print(f"\n{'='*60}")
                _cmd_dry_run(str(fichero))
        else:
            _cmd_procesar_directorio(str(directorio), forzar_completo=args.force_full)

        return 0

    except Exception as exc:
        logger.error("Error inesperado: %s", exc, exc_info=True)
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

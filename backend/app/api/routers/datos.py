"""Router para explorar datos insertados en las tablas destino."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..deps import get_db

router = APIRouter(prefix="/datos", tags=["datos"])


def _tabla_existe(db: Session, tabla: str) -> bool:
    result = db.execute(
        text("SELECT to_regclass(:t)"), {"t": tabla}
    ).scalar()
    return result is not None


def _columnas_tabla(db: Session, tabla: str) -> list[str]:
    rows = db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t "
            "ORDER BY ordinal_position"
        ),
        {"t": tabla},
    ).fetchall()
    return [r[0] for r in rows]


@router.get("/tablas")
def listar_tablas(db: Session = Depends(get_db)):
    """Devuelve las tablas destino conocidas con su número de registros."""
    # Tablas definidas en parsers configurados
    rows = db.execute(
        text(
            "SELECT DISTINCT tabla_destino FROM t_configuracion_parser "
            "WHERE tabla_destino IS NOT NULL AND tabla_destino != '' "
            "ORDER BY tabla_destino"
        )
    ).fetchall()
    tablas_parser = [r[0] for r in rows]

    # Tablas fijas del sistema
    tablas_sistema = ["t_errores", "t_metricas", "t_eventos"]
    todas = sorted(set(tablas_parser + tablas_sistema))

    resultado = []
    for tabla in todas:
        if not _tabla_existe(db, tabla):
            continue
        try:
            count = db.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar()
            resultado.append({"tabla": tabla, "registros": count})
        except Exception:
            resultado.append({"tabla": tabla, "registros": None})

    return resultado


@router.get("/{tabla}")
def obtener_datos(
    tabla: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Devuelve los datos de una tabla destino de forma paginada."""
    # Validar nombre de tabla: solo letras, números y guión bajo
    if not tabla.replace("_", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de tabla inválido.",
        )

    if not _tabla_existe(db, tabla):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La tabla '{tabla}' no existe.",
        )

    columnas = _columnas_tabla(db, tabla)
    if not columnas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron columnas en '{tabla}'.",
        )

    total = db.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar()
    offset = (page - 1) * limit

    rows = db.execute(
        text(f'SELECT * FROM "{tabla}" ORDER BY id DESC LIMIT :limit OFFSET :offset'),
        {"limit": limit, "offset": offset},
    ).fetchall()

    filas = [dict(zip(columnas, row)) for row in rows]

    # Convertir tipos no serializables
    for fila in filas:
        for k, v in fila.items():
            if hasattr(v, "isoformat"):
                fila[k] = v.isoformat()

    return {
        "tabla": tabla,
        "columnas": columnas,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),  # ceil division
        "filas": filas,
    }

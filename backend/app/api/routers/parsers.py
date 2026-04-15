"""Router CRUD para configuración de parsers."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ...models.configuracion_parser import (
    CampoExtraccion,
    ConfiguracionParser,
    FuenteFichero,
    PatronExtraccion,
)
from ..deps import get_db
from ..schemas.parser import (
    CampoExtraccionCrear,
    CampoExtraccionActualizar,
    CampoExtraccionSalida,
    ConfiguracionParserActualizar,
    ConfiguracionParserCrear,
    ConfiguracionParserReemplazar,
    ConfiguracionParserResumen,
    ConfiguracionParserSalida,
    FuenteFicheroCrear,
    FuenteFicheroActualizar,
    FuenteFicheroSalida,
    PatronExtraccionCrear,
    PatronExtraccionActualizar,
    PatronExtraccionSalida,
)

router = APIRouter(prefix="/parsers", tags=["parsers"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_parser_o_404(id_parser: int, db: Session) -> ConfiguracionParser:
    config = (
        db.query(ConfiguracionParser)
        .filter_by(id=id_parser)
        .options(
            joinedload(ConfiguracionParser.patrones),
            joinedload(ConfiguracionParser.campos),
            joinedload(ConfiguracionParser.fuentes),
        )
        .first()
    )
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Parser {id_parser} no encontrado.")
    return config


def _crear_relaciones(config: ConfiguracionParser,
                      patrones: list[PatronExtraccionCrear],
                      campos: list[CampoExtraccionCrear],
                      fuentes: list[FuenteFicheroCrear]) -> None:
    for p in patrones:
        config.patrones.append(PatronExtraccion(**p.model_dump()))
    for c in campos:
        config.campos.append(CampoExtraccion(**c.model_dump()))
    for f in fuentes:
        config.fuentes.append(FuenteFichero(**f.model_dump()))


# ---------------------------------------------------------------------------
# Parser — CRUD principal
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[ConfiguracionParserResumen])
def listar_parsers(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
):
    """Lista todos los parsers con un resumen de sus relaciones."""
    q = db.query(ConfiguracionParser).options(
        joinedload(ConfiguracionParser.patrones),
        joinedload(ConfiguracionParser.campos),
        joinedload(ConfiguracionParser.fuentes),
    )
    if solo_activos:
        q = q.filter_by(activo=True)
    configs = q.order_by(ConfiguracionParser.nombre).all()

    return [
        ConfiguracionParserResumen(
            **{col: getattr(c, col)
               for col in ("id", "nombre", "descripcion", "tabla_destino",
                           "activo", "fecha_creacion", "fecha_modificacion")},
            num_patrones=len(c.patrones),
            num_campos=len(c.campos),
            num_fuentes=len(c.fuentes),
        )
        for c in configs
    ]


@router.post("/", response_model=ConfiguracionParserSalida,
             status_code=status.HTTP_201_CREATED)
def crear_parser(payload: ConfiguracionParserCrear, db: Session = Depends(get_db)):
    """Crea un parser completo con sus patrones, campos y fuentes."""
    if db.query(ConfiguracionParser).filter_by(nombre=payload.nombre).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Ya existe un parser con nombre '{payload.nombre}'.")

    ahora = datetime.now(timezone.utc)
    config = ConfiguracionParser(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        tabla_destino=payload.tabla_destino,
        activo=payload.activo,
        fecha_creacion=ahora,
        fecha_modificacion=ahora,
    )
    db.add(config)
    db.flush()  # obtiene el id antes de añadir relaciones
    _crear_relaciones(config, payload.patrones, payload.campos, payload.fuentes)
    db.commit()
    db.refresh(config)
    return config


@router.get("/{id_parser}", response_model=ConfiguracionParserSalida)
def obtener_parser(id_parser: int, db: Session = Depends(get_db)):
    """Devuelve el detalle completo de un parser."""
    return _get_parser_o_404(id_parser, db)


@router.put("/{id_parser}", response_model=ConfiguracionParserSalida)
def reemplazar_parser(id_parser: int,
                      payload: ConfiguracionParserReemplazar,
                      db: Session = Depends(get_db)):
    """Reemplaza completamente un parser: elimina y recrea patrones, campos y fuentes."""
    config = _get_parser_o_404(id_parser, db)

    # Verificar nombre único si cambia
    if payload.nombre != config.nombre:
        if db.query(ConfiguracionParser).filter_by(nombre=payload.nombre).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Ya existe un parser con nombre '{payload.nombre}'.")

    config.nombre = payload.nombre
    config.descripcion = payload.descripcion
    config.tabla_destino = payload.tabla_destino
    config.activo = payload.activo
    config.fecha_modificacion = datetime.now(timezone.utc)

    # Eliminar relaciones existentes y recrear
    config.patrones.clear()
    config.campos.clear()
    config.fuentes.clear()
    db.flush()
    _crear_relaciones(config, payload.patrones, payload.campos, payload.fuentes)

    db.commit()
    db.refresh(config)
    return config


@router.patch("/{id_parser}", response_model=ConfiguracionParserSalida)
def actualizar_parser(id_parser: int,
                      payload: ConfiguracionParserActualizar,
                      db: Session = Depends(get_db)):
    """Actualiza campos sueltos del parser sin tocar patrones, campos ni fuentes."""
    config = _get_parser_o_404(id_parser, db)

    cambios = payload.model_dump(exclude_none=True)
    if "nombre" in cambios and cambios["nombre"] != config.nombre:
        if db.query(ConfiguracionParser).filter_by(nombre=cambios["nombre"]).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Ya existe un parser con nombre '{cambios['nombre']}'.")

    for campo, valor in cambios.items():
        setattr(config, campo, valor)
    config.fecha_modificacion = datetime.now(timezone.utc)

    db.commit()
    db.refresh(config)
    return config


@router.delete("/{id_parser}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_parser(id_parser: int, db: Session = Depends(get_db)):
    """Elimina un parser y en cascada sus patrones, campos y fuentes."""
    config = _get_parser_o_404(id_parser, db)
    db.delete(config)
    db.commit()


# ---------------------------------------------------------------------------
# Patrones
# ---------------------------------------------------------------------------

@router.post("/{id_parser}/patrones", response_model=PatronExtraccionSalida,
             status_code=status.HTTP_201_CREATED)
def añadir_patron(id_parser: int, payload: PatronExtraccionCrear,
                  db: Session = Depends(get_db)):
    """Añade un patrón de extracción a un parser existente."""
    config = _get_parser_o_404(id_parser, db)
    patron = PatronExtraccion(id_parser=config.id, **payload.model_dump())
    db.add(patron)
    config.fecha_modificacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patron)
    return patron


@router.patch("/{id_parser}/patrones/{id_patron}", response_model=PatronExtraccionSalida)
def actualizar_patron(id_parser: int, id_patron: int,
                      payload: PatronExtraccionActualizar,
                      db: Session = Depends(get_db)):
    """Actualiza un patrón de extracción."""
    _get_parser_o_404(id_parser, db)
    patron = db.query(PatronExtraccion).filter_by(id=id_patron, id_parser=id_parser).first()
    if patron is None:
        raise HTTPException(status_code=404, detail=f"Patrón {id_patron} no encontrado.")
    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(patron, campo, valor)
    db.commit()
    db.refresh(patron)
    return patron


@router.delete("/{id_parser}/patrones/{id_patron}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_patron(id_parser: int, id_patron: int, db: Session = Depends(get_db)):
    """Elimina un patrón de extracción."""
    _get_parser_o_404(id_parser, db)
    patron = db.query(PatronExtraccion).filter_by(id=id_patron, id_parser=id_parser).first()
    if patron is None:
        raise HTTPException(status_code=404, detail=f"Patrón {id_patron} no encontrado.")
    db.delete(patron)
    db.commit()


# ---------------------------------------------------------------------------
# Campos
# ---------------------------------------------------------------------------

@router.post("/{id_parser}/campos", response_model=CampoExtraccionSalida,
             status_code=status.HTTP_201_CREATED)
def añadir_campo(id_parser: int, payload: CampoExtraccionCrear,
                 db: Session = Depends(get_db)):
    """Añade un campo de extracción a un parser existente."""
    config = _get_parser_o_404(id_parser, db)
    campo = CampoExtraccion(id_parser=config.id, **payload.model_dump())
    db.add(campo)
    config.fecha_modificacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(campo)
    return campo


@router.patch("/{id_parser}/campos/{id_campo}", response_model=CampoExtraccionSalida)
def actualizar_campo(id_parser: int, id_campo: int,
                     payload: CampoExtraccionActualizar,
                     db: Session = Depends(get_db)):
    """Actualiza un campo de extracción."""
    _get_parser_o_404(id_parser, db)
    campo = db.query(CampoExtraccion).filter_by(id=id_campo, id_parser=id_parser).first()
    if campo is None:
        raise HTTPException(status_code=404, detail=f"Campo {id_campo} no encontrado.")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(campo, k, v)
    db.commit()
    db.refresh(campo)
    return campo


@router.delete("/{id_parser}/campos/{id_campo}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_campo(id_parser: int, id_campo: int, db: Session = Depends(get_db)):
    """Elimina un campo de extracción."""
    _get_parser_o_404(id_parser, db)
    campo = db.query(CampoExtraccion).filter_by(id=id_campo, id_parser=id_parser).first()
    if campo is None:
        raise HTTPException(status_code=404, detail=f"Campo {id_campo} no encontrado.")
    db.delete(campo)
    db.commit()


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------

@router.post("/{id_parser}/fuentes", response_model=FuenteFicheroSalida,
             status_code=status.HTTP_201_CREATED)
def añadir_fuente(id_parser: int, payload: FuenteFicheroCrear,
                  db: Session = Depends(get_db)):
    """Añade una fuente de fichero a un parser existente."""
    config = _get_parser_o_404(id_parser, db)
    fuente = FuenteFichero(id_parser=config.id, **payload.model_dump())
    db.add(fuente)
    config.fecha_modificacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fuente)
    return fuente


@router.patch("/{id_parser}/fuentes/{id_fuente}", response_model=FuenteFicheroSalida)
def actualizar_fuente(id_parser: int, id_fuente: int,
                      payload: FuenteFicheroActualizar,
                      db: Session = Depends(get_db)):
    """Actualiza una fuente de fichero."""
    _get_parser_o_404(id_parser, db)
    fuente = db.query(FuenteFichero).filter_by(id=id_fuente, id_parser=id_parser).first()
    if fuente is None:
        raise HTTPException(status_code=404, detail=f"Fuente {id_fuente} no encontrada.")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(fuente, k, v)
    db.commit()
    db.refresh(fuente)
    return fuente


@router.delete("/{id_parser}/fuentes/{id_fuente}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_fuente(id_parser: int, id_fuente: int, db: Session = Depends(get_db)):
    """Elimina una fuente de fichero."""
    _get_parser_o_404(id_parser, db)
    fuente = db.query(FuenteFichero).filter_by(id=id_fuente, id_parser=id_parser).first()
    if fuente is None:
        raise HTTPException(status_code=404, detail=f"Fuente {id_fuente} no encontrada.")
    db.delete(fuente)
    db.commit()

"""configuracion_parsers

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t_configuracion_parser",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tabla_destino", sa.String(100), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_modificacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", name="uq_configuracion_parser_nombre"),
    )
    op.create_index(
        "ix_t_configuracion_parser_activo", "t_configuracion_parser", ["activo"]
    )

    op.create_table(
        "t_patron_extraccion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_parser", sa.Integer(), nullable=False),
        sa.Column("expresion_regular", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["id_parser"], ["t_configuracion_parser.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_t_patron_extraccion_id_parser", "t_patron_extraccion", ["id_parser"]
    )

    op.create_table(
        "t_campo_extraccion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_parser", sa.Integer(), nullable=False),
        sa.Column("nombre_grupo", sa.String(100), nullable=False),
        sa.Column("campo_bd", sa.String(100), nullable=False),
        sa.Column("tipo_dato", sa.String(20), nullable=False, server_default="text"),
        sa.Column("longitud", sa.Integer(), nullable=True),
        sa.Column("opcional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("valor_defecto", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["id_parser"], ["t_configuracion_parser.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_t_campo_extraccion_id_parser", "t_campo_extraccion", ["id_parser"]
    )

    op.create_table(
        "t_fuente_fichero",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_parser", sa.Integer(), nullable=False),
        sa.Column("ruta_patron", sa.String(500), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["id_parser"], ["t_configuracion_parser.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_t_fuente_fichero_id_parser", "t_fuente_fichero", ["id_parser"]
    )


def downgrade() -> None:
    op.drop_index("ix_t_fuente_fichero_id_parser", table_name="t_fuente_fichero")
    op.drop_table("t_fuente_fichero")
    op.drop_index("ix_t_campo_extraccion_id_parser", table_name="t_campo_extraccion")
    op.drop_table("t_campo_extraccion")
    op.drop_index("ix_t_patron_extraccion_id_parser", table_name="t_patron_extraccion")
    op.drop_table("t_patron_extraccion")
    op.drop_index("ix_t_configuracion_parser_activo", table_name="t_configuracion_parser")
    op.drop_table("t_configuracion_parser")

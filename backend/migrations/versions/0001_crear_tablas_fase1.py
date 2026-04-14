"""crear_tablas_fase1

Revision ID: 0001
Revises:
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t_control_carga",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_ejecucion", sa.String(36), nullable=False),
        sa.Column("ruta_fichero", sa.String(500), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="EN_PROCESO"),
        sa.Column("ultima_linea", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lineas_procesadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registros_insertados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mensaje_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_t_control_carga_id_ejecucion", "t_control_carga", ["id_ejecucion"])
    op.create_index("ix_t_control_carga_ruta_fichero", "t_control_carga", ["ruta_fichero"])

    op.create_table(
        "t_errores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nivel", sa.String(20), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("componente", sa.String(255), nullable=True),
        sa.Column("origen_fichero", sa.String(500), nullable=False),
        sa.Column("num_linea", sa.Integer(), nullable=False),
        sa.Column("id_ejecucion", sa.String(36), nullable=False),
        sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "t_metricas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nombre_metrica", sa.String(255), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("unidad", sa.String(50), nullable=True),
        sa.Column("componente", sa.String(255), nullable=True),
        sa.Column("origen_fichero", sa.String(500), nullable=False),
        sa.Column("num_linea", sa.Integer(), nullable=False),
        sa.Column("id_ejecucion", sa.String(36), nullable=False),
        sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "t_eventos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tipo_evento", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("usuario", sa.String(255), nullable=True),
        sa.Column("componente", sa.String(255), nullable=True),
        sa.Column("origen_fichero", sa.String(500), nullable=False),
        sa.Column("num_linea", sa.Integer(), nullable=False),
        sa.Column("id_ejecucion", sa.String(36), nullable=False),
        sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("t_eventos")
    op.drop_table("t_metricas")
    op.drop_table("t_errores")
    op.drop_index("ix_t_control_carga_ruta_fichero", table_name="t_control_carga")
    op.drop_index("ix_t_control_carga_id_ejecucion", table_name="t_control_carga")
    op.drop_table("t_control_carga")

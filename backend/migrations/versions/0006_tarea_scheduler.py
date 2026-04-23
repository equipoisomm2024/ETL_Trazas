"""tabla t_tarea_scheduler para procesamiento programado con APScheduler

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t_tarea_scheduler",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(100), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("tipo_fuente", sa.String(20), nullable=False, server_default="fuentes_bd"),
        sa.Column("ruta", sa.String(500), nullable=True),
        sa.Column(
            "id_parser",
            sa.Integer,
            sa.ForeignKey("t_configuracion_parser.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("forzar_completo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ultima_ejecucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proxima_ejecucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "fecha_modificacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("t_tarea_scheduler")

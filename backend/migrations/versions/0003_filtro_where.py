"""filtro_where y separador_campos en t_configuracion_parser

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "t_configuracion_parser",
        sa.Column("separador_campos", sa.String(20), nullable=True, server_default=" "),
    )
    op.add_column(
        "t_configuracion_parser",
        sa.Column("filtro_where", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("t_configuracion_parser", "filtro_where")
    op.drop_column("t_configuracion_parser", "separador_campos")

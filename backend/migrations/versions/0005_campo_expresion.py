"""expresion y nombre_grupo nullable en t_campo_extraccion (campos calculados)

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "t_campo_extraccion",
        sa.Column("expresion", sa.Text, nullable=True),
    )
    op.alter_column(
        "t_campo_extraccion",
        "nombre_grupo",
        existing_type=sa.String(100),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "t_campo_extraccion",
        "nombre_grupo",
        existing_type=sa.String(100),
        nullable=False,
    )
    op.drop_column("t_campo_extraccion", "expresion")

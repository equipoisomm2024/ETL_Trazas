"""nombres_grupos_union en t_campo_extraccion para unions no contiguas

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "t_campo_extraccion",
        sa.Column("nombres_grupos_union", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("t_campo_extraccion", "nombres_grupos_union")

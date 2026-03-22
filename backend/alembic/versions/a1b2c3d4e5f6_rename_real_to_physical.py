"""rename production_type real to physical

Revision ID: a1b2c3d4e5f6
Revises: d45f79e0923e
Create Date: 2026-03-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d45f79e0923e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE productions SET production_type = 'physical' WHERE production_type = 'real'")
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE productions SET production_type = 'real' WHERE production_type = 'physical'")
    )

"""add auth_id to users

Revision ID: b4c2d3e5f6a7
Revises: a3b1c2d4e5f6
Create Date: 2026-03-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c2d3e5f6a7"
down_revision: str | None = "a3b1c2d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_users_auth_id", "users", ["auth_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_auth_id", "users", type_="unique")
    op.drop_column("users", "auth_id")

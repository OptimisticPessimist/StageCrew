"""add_scene_character_mapping

Revision ID: a3b1c2d4e5f6
Revises: 516b07809f13
Create Date: 2026-03-25 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b1c2d4e5f6"
down_revision: str | None = "516b07809f13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scene_character_mappings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scene_id", sa.UUID(), nullable=False),
        sa.Column("character_id", sa.UUID(), nullable=False),
        sa.Column("appearance_type", sa.String(length=16), nullable=False, server_default="dialogue"),
        sa.Column("is_auto_generated", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_id", "character_id", name="uq_scene_character_mapping"),
    )


def downgrade() -> None:
    op.drop_table("scene_character_mappings")

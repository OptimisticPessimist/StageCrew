"""add event and availability models

Revision ID: c5d6e7f8a9b0
Revises: b4c2d3e5f6a7
Create Date: 2026-04-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "b4c2d3e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("production_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False, server_default="rehearsal"),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_all_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("location_name", sa.String(length=256), nullable=True),
        sa.Column("location_url", sa.String(length=512), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["production_id"], ["productions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_production_id", "events", ["production_id"])
    op.create_index("ix_events_start_at", "events", ["start_at"])

    op.create_table(
        "event_attendees",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("attendance_type", sa.String(length=16), nullable=False, server_default="required"),
        sa.Column("rsvp_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("actual_attendance", sa.String(length=16), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_attendee"),
    )

    op.create_table(
        "event_scenes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("scene_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "scene_id", name="uq_event_scene"),
    )

    op.create_table(
        "user_availabilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("production_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("availability", sa.String(length=16), nullable=False, server_default="available"),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["production_id"], ["productions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "production_id", "date", name="uq_user_availability_per_day"),
    )
    # マネージャーが公演メンバー全員分の範囲を取得するクエリ用の補助インデックス。
    # (user_id, production_id, date) の組み合わせは UniqueConstraint が担うため重複を避ける。
    op.create_index(
        "ix_user_availabilities_prod_date",
        "user_availabilities",
        ["production_id", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_availabilities_prod_date", table_name="user_availabilities")
    op.drop_table("user_availabilities")
    op.drop_table("event_scenes")
    op.drop_table("event_attendees")
    op.drop_index("ix_events_start_at", table_name="events")
    op.drop_index("ix_events_production_id", table_name="events")
    op.drop_table("events")

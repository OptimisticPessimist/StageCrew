import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


# ============================================================
# User
# ============================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(128))
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    org_memberships: Mapped[list["OrganizationMembership"]] = relationship(back_populates="user")


# ============================================================
# Organization (団体)
# ============================================================
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cast_default_capabilities: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["task.view", "task.edit_own", "task.create", "comment.create"]
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["OrganizationMembership"]] = relationship(back_populates="organization")
    productions: Mapped[list["Production"]] = relationship(back_populates="organization")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="organization")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    org_role: Mapped[str] = mapped_column(String(32), default="member")  # owner | admin | member
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="org_memberships")
    organization: Mapped["Organization"] = relationship(back_populates="members")


# ============================================================
# Invitation (招待)
# ============================================================
class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    org_role: Mapped[str] = mapped_column(String(32), default="member")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | accepted | expired
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="invitations")
    inviter: Mapped["User"] = relationship()


# ============================================================
# Production (公演)
# ============================================================
class Production(Base):
    __tablename__ = "productions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    production_type: Mapped[str] = mapped_column(String(16), default="physical")  # physical | vr | hybrid
    opening_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_phase: Mapped[str | None] = mapped_column(String(64), nullable=True)
    discord_webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="productions")
    departments: Mapped[list["Department"]] = relationship(back_populates="production")
    production_memberships: Mapped[list["ProductionMembership"]] = relationship(back_populates="production")
    phases: Mapped[list["ProductionPhase"]] = relationship(back_populates="production")
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="production")
    issues: Mapped[list["Issue"]] = relationship(back_populates="production")
    labels: Mapped[list["Label"]] = relationship(back_populates="production")
    scripts: Mapped[list["Script"]] = relationship(back_populates="production")


# ============================================================
# Production Membership (公演メンバーシップ)
# ============================================================
class ProductionMembership(Base):
    __tablename__ = "production_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    production_role: Mapped[str] = mapped_column(String(32), default="member")  # manager | member
    is_cast: Mapped[bool] = mapped_column(Boolean, default=False)
    cast_capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    production: Mapped["Production"] = relationship(back_populates="production_memberships")
    department_memberships: Mapped[list["DepartmentMembership"]] = relationship(back_populates="production_membership")


# ============================================================
# Department (部門)
# ============================================================
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex color
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    production: Mapped["Production"] = relationship(back_populates="departments")
    staff_roles: Mapped[list["StaffRole"]] = relationship(back_populates="department")
    members: Mapped[list["DepartmentMembership"]] = relationship(back_populates="department")
    status_flow: Mapped[list["StatusDefinition"]] = relationship(back_populates="department")


class StaffRole(Base):
    __tablename__ = "staff_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    department: Mapped["Department"] = relationship(back_populates="staff_roles")


class DepartmentMembership(Base):
    __tablename__ = "department_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production_memberships.id", ondelete="CASCADE")
    )
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"))
    staff_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_roles.id", ondelete="SET NULL"), nullable=True
    )
    capabilities: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=["task.view", "task.create", "task.edit_dept", "task.assign", "comment.create"],
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    production_membership: Mapped["ProductionMembership"] = relationship(back_populates="department_memberships")
    department: Mapped["Department"] = relationship(back_populates="members")
    staff_role: Mapped["StaffRole | None"] = relationship()


# ============================================================
# Status Definition (カスタムステータス)
# ============================================================
class StatusDefinition(Base):
    __tablename__ = "status_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    )
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)  # True for "完了" etc.

    department: Mapped["Department | None"] = relationship(back_populates="status_flow")


# ============================================================
# Production Phase (公演フェーズ)
# ============================================================
class ProductionPhase(Base):
    __tablename__ = "production_phases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    production: Mapped["Production"] = relationship(back_populates="phases")


# ============================================================
# Milestone (マイルストーン)
# ============================================================
class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    production: Mapped["Production"] = relationship(back_populates="milestones")


# ============================================================
# Label (ラベル)
# ============================================================
class Label(Base):
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    production: Mapped["Production"] = relationship(back_populates="labels")


# ============================================================
# Issue (課題)
# ============================================================
class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    parent_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
    )
    phase_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("production_phases.id", ondelete="SET NULL"), nullable=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True
    )
    status_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("status_definitions.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_type: Mapped[str] = mapped_column(String(32), default="task")  # task | bug | request | notice
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # high | medium | low
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    production: Mapped["Production"] = relationship(back_populates="issues")
    department: Mapped["Department | None"] = relationship()
    parent_issue: Mapped["Issue | None"] = relationship(remote_side="Issue.id")
    phase: Mapped["ProductionPhase | None"] = relationship()
    milestone: Mapped["Milestone | None"] = relationship()
    status: Mapped["StatusDefinition | None"] = relationship()
    creator: Mapped["User"] = relationship()
    assignees: Mapped[list["IssueAssignee"]] = relationship(back_populates="issue")
    comments: Mapped[list["Comment"]] = relationship(back_populates="issue")
    issue_labels: Mapped[list["IssueLabel"]] = relationship(back_populates="issue")
    dependencies_as_blocker: Mapped[list["IssueDependency"]] = relationship(
        foreign_keys="IssueDependency.blocker_issue_id", back_populates="blocker"
    )
    dependencies_as_blocked: Mapped[list["IssueDependency"]] = relationship(
        foreign_keys="IssueDependency.blocked_issue_id", back_populates="blocked"
    )


class IssueAssignee(Base):
    __tablename__ = "issue_assignees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    issue: Mapped["Issue"] = relationship(back_populates="assignees")
    user: Mapped["User"] = relationship()


class IssueLabel(Base):
    __tablename__ = "issue_labels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    label_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labels.id", ondelete="CASCADE"))

    issue: Mapped["Issue"] = relationship(back_populates="issue_labels")
    label: Mapped["Label"] = relationship()


class IssueDependency(Base):
    __tablename__ = "issue_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    blocked_issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))

    blocker: Mapped["Issue"] = relationship(foreign_keys=[blocker_issue_id], back_populates="dependencies_as_blocker")
    blocked: Mapped["Issue"] = relationship(foreign_keys=[blocked_issue_id], back_populates="dependencies_as_blocked")


# ============================================================
# Comment (コメント)
# ============================================================
class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    issue: Mapped["Issue"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship()


# ============================================================
# Script (脚本)
# ============================================================
class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productions.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    draft_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    revision_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    copyright: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_orientation: Mapped[str] = mapped_column(String(16), default="landscape")  # landscape | portrait
    pdf_writing_direction: Mapped[str] = mapped_column(String(16), default="vertical")  # vertical | horizontal
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_contact: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    production: Mapped["Production"] = relationship(back_populates="scripts")
    uploader: Mapped["User"] = relationship()
    scenes: Mapped[list["Scene"]] = relationship(back_populates="script", cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship(back_populates="script", cascade="all, delete-orphan")


# ============================================================
# Scene (シーン)
# ============================================================
class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"))
    act_number: Mapped[int] = mapped_column(Integer, default=1)
    scene_number: Mapped[int] = mapped_column(Integer, default=1)
    heading: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    script: Mapped["Script"] = relationship(back_populates="scenes")
    lines: Mapped[list["Line"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


# ============================================================
# Character (登場人物)
# ============================================================
class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    script: Mapped["Script"] = relationship(back_populates="characters")
    lines: Mapped[list["Line"]] = relationship(back_populates="character")


# ============================================================
# Line (セリフ)
# ============================================================
class Line(Base):
    __tablename__ = "lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"))
    character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scene: Mapped["Scene"] = relationship(back_populates="lines")
    character: Mapped["Character | None"] = relationship(back_populates="lines")

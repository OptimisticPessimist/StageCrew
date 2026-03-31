"""Periodic deadline reminder service."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.db.base import async_session
from src.db.models import (
    Issue,
    IssueAssignee,
    Production,
    StatusDefinition,
)
from src.services.discord_webhook import notify_deadline_reminder

logger = logging.getLogger(__name__)

ADVISORY_LOCK_ID = 842_021_517


def _normalize_utc(value: datetime) -> datetime:
    """Convert a timestamp to UTC while handling naive SQLite test values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _days_remaining(due_date: datetime, now: datetime) -> int:
    """Return the number of calendar days from now until the due date in UTC."""
    due_day = _normalize_utc(due_date).date()
    now_day = _normalize_utc(now).date()
    return (due_day - now_day).days


async def _try_acquire_lock(db: AsyncSession) -> bool:
    """Use a Postgres advisory lock so only one app instance sends reminders."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return True
    result = await db.execute(select(func.pg_try_advisory_lock(ADVISORY_LOCK_ID)))
    return bool(result.scalar())


async def _release_lock(db: AsyncSession) -> None:
    """Release the advisory lock when the check completes."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    await db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": ADVISORY_LOCK_ID})


async def _run_check() -> None:
    """Query issues with approaching deadlines and send reminders."""
    now = datetime.now(UTC)

    async with async_session() as db:
        if not await _try_acquire_lock(db):
            logger.info("Skipping deadline reminder check on this instance; another node holds the lock")
            return

        try:
            await _check_and_notify(db, now)
        finally:
            await _release_lock(db)


async def _check_and_notify(db: AsyncSession, now: datetime) -> None:
    """Core logic: find due-soon issues and send notifications per production."""
    max_days = max(settings.deadline_reminder_days)
    cutoff = now + timedelta(days=max_days + 1)

    closed_status_ids = select(StatusDefinition.id).where(StatusDefinition.is_closed.is_(True))

    stmt = (
        select(Issue)
        .where(
            Issue.due_date.isnot(None),
            Issue.due_date <= cutoff,
            or_(Issue.status_id.is_(None), Issue.status_id.notin_(closed_status_ids)),
        )
        .options(
            selectinload(Issue.assignees).selectinload(IssueAssignee.user),
            selectinload(Issue.production),
        )
    )
    result = await db.execute(stmt)
    issues = result.scalars().unique().all()

    by_production: dict[str, list[dict]] = {}
    productions: dict[str, Production] = {}

    for issue in issues:
        if not issue.due_date:
            continue

        days_remaining = _days_remaining(issue.due_date, now)
        if days_remaining > max_days:
            continue

        should_notify = days_remaining < 0 or days_remaining in settings.deadline_reminder_days
        if not should_notify:
            continue

        prod_id = str(issue.production_id)
        if prod_id not in by_production:
            by_production[prod_id] = []
            productions[prod_id] = issue.production

        assignee_names = [a.user.display_name for a in issue.assignees]

        by_production[prod_id].append(
            {
                "title": issue.title,
                "due_date": issue.due_date.isoformat(),
                "assignee_names": assignee_names,
                "days_remaining": days_remaining,
            }
        )

    for prod_id, issue_list in by_production.items():
        production = productions[prod_id]
        if not production.discord_webhook_url:
            continue

        issue_list.sort(key=lambda x: x["days_remaining"])

        notify_deadline_reminder(
            production.discord_webhook_url,
            issues=issue_list,
            production_name=production.name,
        )
        logger.info(
            "Sent deadline reminder for production '%s' (%d issues)",
            production.name,
            len(issue_list),
        )


async def deadline_reminder_loop() -> None:
    """Run the deadline check once daily at the configured UTC hour.

    注意: 本番環境では Supabase pg_cron + pg_net で実行されるため、
    この関数はローカル開発・テスト用途でのみ使用される。
    """
    logger.info(
        "Deadline reminder started (check hour: %02d:00 UTC, days: %s)",
        settings.deadline_reminder_hour_utc,
        settings.deadline_reminder_days,
    )

    while True:
        now = datetime.now(UTC)
        target = now.replace(
            hour=settings.deadline_reminder_hour_utc,
            minute=0,
            second=0,
            microsecond=0,
        )
        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        logger.debug("Next deadline check in %.0f seconds", wait_seconds)

        await asyncio.sleep(wait_seconds)

        try:
            await _run_check()
        except Exception:
            logger.exception("Deadline reminder check failed")

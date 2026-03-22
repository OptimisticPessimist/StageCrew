"""Periodic deadline reminder service.

Runs as an asyncio background task within the FastAPI lifespan.
Checks once daily (at a configurable UTC hour) for issues approaching
their due dates and sends Discord webhook notifications.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
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


async def _run_check() -> None:
    """Query issues with approaching deadlines and send reminders."""
    now = datetime.now(UTC)

    async with async_session() as db:
        await _check_and_notify(db, now)


async def _check_and_notify(db: AsyncSession, now: datetime) -> None:
    """Core logic: find due-soon issues and send notifications per production."""
    max_days = max(settings.deadline_reminder_days)
    cutoff = now + timedelta(days=max_days + 1)

    # Get all open issues with due dates within the reminder window
    # Subquery for closed status IDs
    closed_status_ids = select(StatusDefinition.id).where(StatusDefinition.is_closed.is_(True))

    stmt = (
        select(Issue)
        .where(
            Issue.due_date.isnot(None),
            Issue.due_date <= cutoff,
            Issue.status_id.notin_(closed_status_ids),
        )
        .options(
            selectinload(Issue.assignees).selectinload(IssueAssignee.user),
            selectinload(Issue.production),
        )
    )
    result = await db.execute(stmt)
    issues = result.scalars().unique().all()

    # Group by production
    by_production: dict[str, list[dict]] = {}
    productions: dict[str, Production] = {}

    for issue in issues:
        if not issue.due_date:
            continue

        days_remaining = (issue.due_date.replace(tzinfo=UTC) - now).days

        # Only include if days_remaining matches one of the configured thresholds
        # or if already overdue
        if days_remaining > max_days:
            continue

        should_notify = days_remaining <= 0 or any(
            days_remaining <= d for d in settings.deadline_reminder_days
        )
        if not should_notify:
            continue

        prod_id = str(issue.production_id)
        if prod_id not in by_production:
            by_production[prod_id] = []
            productions[prod_id] = issue.production

        assignee_names = [a.user.display_name for a in issue.assignees]

        by_production[prod_id].append({
            "title": issue.title,
            "due_date": issue.due_date.isoformat(),
            "assignee_names": assignee_names,
            "days_remaining": days_remaining,
        })

    # Send notifications
    for prod_id, issue_list in by_production.items():
        production = productions[prod_id]
        if not production.discord_webhook_url:
            continue

        # Sort: overdue first, then by days remaining
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
    """Background loop that runs the deadline check once daily at the configured UTC hour."""
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

"""Discord Webhook notification service.

Sends embed-formatted notifications to Discord channels via webhook URLs.
All sends are fire-and-forget: errors are logged but never raised to callers.
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

# Color-blind friendly palette (Wong palette)
PRIORITY_COLORS = {
    "high": 0xD55E00,    # vermillion
    "medium": 0xE69F00,  # amber
    "low": 0x0072B2,     # blue
}
COLOR_UPDATE = 0x56B4E9       # sky blue
COLOR_COMPLETED = 0x009E73    # bluish green
COLOR_COMMENT = 0xCC79A7      # reddish purple
COLOR_REMINDER = 0xD55E00     # vermillion

ISSUE_TYPE_LABELS = {
    "task": "\u30bf\u30b9\u30af",
    "bug": "\u30d0\u30b0\u30fb\u554f\u984c",
    "request": "\u8981\u671b",
    "notice": "\u9023\u7d61\u4e8b\u9805",
}

PRIORITY_LABELS = {
    "high": "\u9ad8",
    "medium": "\u4e2d",
    "low": "\u4f4e",
}


async def _send_webhook(webhook_url: str, payload: dict) -> None:
    """POST payload to Discord webhook URL. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 400:
                logger.warning("Discord webhook failed: %s %s", resp.status_code, resp.text)
    except Exception:
        logger.exception("Discord webhook error")


def fire_and_forget(webhook_url: str | None, payload: dict) -> None:
    """Schedule webhook send as a background task. No-op if webhook_url is None."""
    if not webhook_url:
        return
    asyncio.create_task(_send_webhook(webhook_url, payload))


def notify_issue_created(
    webhook_url: str | None,
    *,
    title: str,
    issue_type: str,
    priority: str,
    department_name: str | None,
    assignee_names: list[str],
    creator_name: str,
) -> None:
    """Send notification when an issue is created."""
    type_label = ISSUE_TYPE_LABELS.get(issue_type, issue_type)
    priority_label = PRIORITY_LABELS.get(priority, priority)
    color = PRIORITY_COLORS.get(priority, COLOR_UPDATE)

    fields = [
        {"name": "\u7a2e\u5225", "value": type_label, "inline": True},
        {"name": "\u512a\u5148\u5ea6", "value": priority_label, "inline": True},
    ]
    if department_name:
        fields.append({"name": "\u90e8\u9580", "value": department_name, "inline": True})
    if assignee_names:
        fields.append({"name": "\u62c5\u5f53\u8005", "value": "\u3001".join(assignee_names), "inline": False})

    payload = {
        "embeds": [
            {
                "title": f"\u2795 \u65b0\u898f\u8ab2\u984c: {title}",
                "color": color,
                "fields": fields,
                "footer": {"text": f"\u4f5c\u6210\u8005: {creator_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    fire_and_forget(webhook_url, payload)


def notify_issue_updated(
    webhook_url: str | None,
    *,
    title: str,
    changes: dict[str, tuple[str, str]],
    updater_name: str,
) -> None:
    """Send notification when an issue is updated.

    changes: mapping of field_label -> (old_value, new_value)
    """
    if not changes:
        return

    fields = [
        {"name": label, "value": f"{old} \u2192 {new}", "inline": False}
        for label, (old, new) in changes.items()
    ]

    payload = {
        "embeds": [
            {
                "title": f"\u270f\ufe0f \u8ab2\u984c\u66f4\u65b0: {title}",
                "color": COLOR_UPDATE,
                "fields": fields,
                "footer": {"text": f"\u66f4\u65b0\u8005: {updater_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    fire_and_forget(webhook_url, payload)


def notify_issue_completed(
    webhook_url: str | None,
    *,
    title: str,
    status_name: str,
    completer_name: str,
) -> None:
    """Send notification when an issue is marked as completed (is_closed=True)."""
    payload = {
        "embeds": [
            {
                "title": f"\u2705 \u5b8c\u4e86: {title}",
                "color": COLOR_COMPLETED,
                "fields": [
                    {"name": "\u30b9\u30c6\u30fc\u30bf\u30b9", "value": status_name, "inline": True},
                ],
                "footer": {"text": f"\u5b8c\u4e86\u8005: {completer_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    fire_and_forget(webhook_url, payload)


def notify_comment_added(
    webhook_url: str | None,
    *,
    issue_title: str,
    comment_content: str,
    commenter_name: str,
) -> None:
    """Send notification when a comment is added to an issue."""
    truncated = comment_content[:200] + ("..." if len(comment_content) > 200 else "")

    payload = {
        "embeds": [
            {
                "title": f"\U0001f4ac \u30b3\u30e1\u30f3\u30c8: {issue_title}",
                "color": COLOR_COMMENT,
                "description": truncated,
                "footer": {"text": f"\u6295\u7a3f\u8005: {commenter_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    fire_and_forget(webhook_url, payload)


def notify_deadline_reminder(
    webhook_url: str | None,
    *,
    issues: list[dict],
    production_name: str,
) -> None:
    """Send deadline reminder notification.

    issues: list of dicts with keys: title, due_date, assignee_names, days_remaining
    """
    if not issues:
        return

    lines = []
    for issue in issues:
        days = issue["days_remaining"]
        assignees = "\u3001".join(issue["assignee_names"]) if issue["assignee_names"] else "\u672a\u5272\u5f53"
        if days <= 0:
            lines.append(f"\u203c\ufe0f **\u671f\u9650\u8d85\u904e**: {issue['title']} (\u62c5\u5f53: {assignees})")
        elif days == 1:
            lines.append(f"\u26a0\ufe0f **\u660e\u65e5\u671f\u9650**: {issue['title']} (\u62c5\u5f53: {assignees})")
        else:
            lines.append(f"\U0001f4c5 **\u3042\u3068{days}\u65e5**: {issue['title']} (\u62c5\u5f53: {assignees})")

    payload = {
        "embeds": [
            {
                "title": f"\u23f0 \u671f\u9650\u30ea\u30de\u30a4\u30f3\u30c0\u30fc: {production_name}",
                "color": COLOR_REMINDER,
                "description": "\n".join(lines),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    fire_and_forget(webhook_url, payload)

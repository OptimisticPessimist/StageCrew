"""Discord Webhook notification service.

Sends embed-formatted notifications to Discord channels via webhook URLs.
All sends are fire-and-forget: errors are logged but never raised to callers.

Notifications from API endpoints are queued via a ContextVar and only dispatched
after the DB transaction commits (see ``get_db``).  Code running outside a
request context (e.g. ``deadline_reminder_loop``) sends immediately.
"""

import asyncio
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

# ---- Webhook queue (post-commit dispatch) ----

_pending: ContextVar[list[tuple[str, dict]]] = ContextVar("discord_pending")

# Discord embed description limit
_EMBED_DESC_MAX = 4096


def init_webhook_queue() -> None:
    """Initialise a per-request queue.  Call at the start of ``get_db``."""
    _pending.set([])


async def send_queued_webhooks() -> None:
    """Fire all queued webhooks.  Call after ``session.commit()``."""
    try:
        queue = _pending.get()
    except LookupError:
        return
    for url, payload in queue:
        asyncio.create_task(_send_webhook(url, payload))
    queue.clear()


def discard_webhook_queue() -> None:
    """Drop queued webhooks (e.g. on rollback)."""
    try:
        _pending.get().clear()
    except LookupError:
        pass


# ---- Color-blind friendly palette (Wong palette) ----

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
    "task": "タスク",
    "bug": "バグ・問題",
    "request": "要望",
    "notice": "連絡事項",
}

PRIORITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
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


def _enqueue(webhook_url: str | None, payload: dict) -> None:
    """Add a webhook payload to the per-request queue.

    If no queue exists (outside a request context, e.g. deadline reminder loop),
    the payload is sent immediately via ``asyncio.create_task``.
    """
    if not webhook_url:
        return
    try:
        _pending.get().append((webhook_url, payload))
    except LookupError:
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
        {"name": "種別", "value": type_label, "inline": True},
        {"name": "優先度", "value": priority_label, "inline": True},
    ]
    if department_name:
        fields.append({"name": "部門", "value": department_name, "inline": True})
    if assignee_names:
        fields.append({"name": "担当者", "value": "、".join(assignee_names), "inline": False})

    payload = {
        "embeds": [
            {
                "title": f"➕ 新規課題: {title}",
                "color": color,
                "fields": fields,
                "footer": {"text": f"作成者: {creator_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    _enqueue(webhook_url, payload)


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
        {"name": label, "value": f"{old} → {new}", "inline": False}
        for label, (old, new) in changes.items()
    ]

    payload = {
        "embeds": [
            {
                "title": f"✏️ 課題更新: {title}",
                "color": COLOR_UPDATE,
                "fields": fields,
                "footer": {"text": f"更新者: {updater_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    _enqueue(webhook_url, payload)


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
                "title": f"✅ 完了: {title}",
                "color": COLOR_COMPLETED,
                "fields": [
                    {"name": "ステータス", "value": status_name, "inline": True},
                ],
                "footer": {"text": f"完了者: {completer_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    _enqueue(webhook_url, payload)


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
                "title": f"💬 コメント: {issue_title}",
                "color": COLOR_COMMENT,
                "description": truncated,
                "footer": {"text": f"投稿者: {commenter_name}"},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
    }
    _enqueue(webhook_url, payload)


def notify_deadline_reminder(
    webhook_url: str | None,
    *,
    issues: list[dict],
    production_name: str,
) -> None:
    """Send deadline reminder notification.

    issues: list of dicts with keys: title, due_date, assignee_names, days_remaining.
    Splits into multiple messages when the description exceeds Discord's 4096
    character limit.
    """
    if not issues:
        return

    lines: list[str] = []
    for issue in issues:
        days = issue["days_remaining"]
        assignees = "、".join(issue["assignee_names"]) if issue["assignee_names"] else "未割当"
        if days < 0:
            line = f"‼️ **期限超過**: {issue['title']} (担当: {assignees})"
        elif days == 0:
            line = f"🚨 **本日期限**: {issue['title']} (担当: {assignees})"
        elif days == 1:
            line = f"⚠️ **明日期限**: {issue['title']} (担当: {assignees})"
        else:
            line = f"📅 **あと{days}日**: {issue['title']} (担当: {assignees})"

        # Truncate single lines that exceed the embed description limit
        if len(line) > _EMBED_DESC_MAX:
            line = line[: _EMBED_DESC_MAX - 1] + "…"
        lines.append(line)

    # Split lines into chunks that fit within Discord's embed description limit
    chunks: list[list[str]] = []
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        # +1 for the newline separator
        line_len = len(line) + (1 if current_chunk else 0)
        if current_chunk and current_len + line_len > _EMBED_DESC_MAX:
            chunks.append(current_chunk)
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append(current_chunk)

    now_iso = datetime.now(UTC).isoformat()
    for i, chunk in enumerate(chunks):
        title = f"⏰ 期限リマインダー: {production_name}"
        if len(chunks) > 1:
            title += f" ({i + 1}/{len(chunks)})"

        payload = {
            "embeds": [
                {
                    "title": title,
                    "color": COLOR_REMINDER,
                    "description": "\n".join(chunk),
                    "timestamp": now_iso,
                }
            ]
        }
        _enqueue(webhook_url, payload)

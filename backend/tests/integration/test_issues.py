"""課題 CRUD エンドポイントのテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Department,
    Issue,
    IssueAssignee,
    Label,
    StatusDefinition,
    User,
)


def _issues_url(org_id, prod_id, suffix=""):
    return f"/api/organizations/{org_id}/productions/{prod_id}/issues{suffix}"


# ---- 一覧 ----


async def test_list_issues_empty(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(_issues_url(prod.organization_id, prod.id, "/"))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_issue_minimal(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        _issues_url(prod.organization_id, prod.id, "/"),
        json={"title": "最小の課題"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "最小の課題"
    assert data["issue_type"] == "task"
    assert data["priority"] == "medium"


async def test_create_issue_full(
    client: AsyncClient, production, department: Department, status_def: StatusDefinition, test_user: User
):
    prod, _ = production
    resp = await client.post(
        _issues_url(prod.organization_id, prod.id, "/"),
        json={
            "title": "完全な課題",
            "description": "詳細説明",
            "issue_type": "bug",
            "priority": "high",
            "status_id": str(status_def.id),
            "department_id": str(department.id),
            "assignee_ids": [str(test_user.id)],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "完全な課題"
    assert data["issue_type"] == "bug"
    assert data["priority"] == "high"
    assert data["status_id"] == str(status_def.id)
    assert data["department_id"] == str(department.id)
    assert len(data["assignees"]) == 1


# ---- 詳細取得 ----


async def test_get_issue(client: AsyncClient, production, db_session: AsyncSession, test_user: User):
    prod, _ = production
    issue = Issue(production_id=prod.id, title="取得テスト", created_by=test_user.id)
    db_session.add(issue)
    await db_session.flush()

    resp = await client.get(_issues_url(prod.organization_id, prod.id, f"/{issue.id}"))
    assert resp.status_code == 200
    assert resp.json()["title"] == "取得テスト"


async def test_get_issue_not_found(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(_issues_url(prod.organization_id, prod.id, f"/{uuid.uuid4()}"))
    assert resp.status_code == 404


# ---- 更新 ----


async def test_update_issue(client: AsyncClient, production, db_session: AsyncSession, test_user: User):
    prod, _ = production
    issue = Issue(production_id=prod.id, title="更新前", created_by=test_user.id)
    db_session.add(issue)
    await db_session.flush()

    resp = await client.patch(
        _issues_url(prod.organization_id, prod.id, f"/{issue.id}"),
        json={"title": "更新後", "priority": "high"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新後"
    assert resp.json()["priority"] == "high"


async def test_update_issue_assignees(
    client: AsyncClient, production, db_session: AsyncSession, test_user: User, other_user: User
):
    prod, _ = production
    issue = Issue(production_id=prod.id, title="アサイン変更", created_by=test_user.id)
    db_session.add(issue)
    await db_session.flush()
    db_session.add(IssueAssignee(issue_id=issue.id, user_id=test_user.id))
    await db_session.flush()

    # other_userをアサインに差し替え
    resp = await client.patch(
        _issues_url(prod.organization_id, prod.id, f"/{issue.id}"),
        json={"assignee_ids": [str(other_user.id)]},
    )
    assert resp.status_code == 200
    assignees = resp.json()["assignees"]
    assert len(assignees) == 1
    assert assignees[0]["user_id"] == str(other_user.id)


async def test_update_issue_labels(client: AsyncClient, production, db_session: AsyncSession, test_user: User):
    prod, _ = production
    label = Label(production_id=prod.id, name="バグ", color="#FF0000")
    db_session.add(label)
    await db_session.flush()

    issue = Issue(production_id=prod.id, title="ラベルテスト", created_by=test_user.id)
    db_session.add(issue)
    await db_session.flush()

    resp = await client.patch(
        _issues_url(prod.organization_id, prod.id, f"/{issue.id}"),
        json={"label_ids": [str(label.id)]},
    )
    assert resp.status_code == 200
    labels = resp.json()["labels"]
    assert len(labels) == 1
    assert labels[0]["name"] == "バグ"


# ---- 削除 ----


async def test_delete_issue(client: AsyncClient, production, db_session: AsyncSession, test_user: User):
    prod, _ = production
    issue = Issue(production_id=prod.id, title="削除テスト", created_by=test_user.id)
    db_session.add(issue)
    await db_session.flush()

    resp = await client.delete(_issues_url(prod.organization_id, prod.id, f"/{issue.id}"))
    assert resp.status_code == 204


# ---- フィルタ ----


async def test_list_issues_filter_by_type(client: AsyncClient, production, db_session: AsyncSession, test_user: User):
    prod, _ = production
    db_session.add(Issue(production_id=prod.id, title="タスク", issue_type="task", created_by=test_user.id))
    db_session.add(Issue(production_id=prod.id, title="バグ", issue_type="bug", created_by=test_user.id))
    await db_session.flush()

    resp = await client.get(_issues_url(prod.organization_id, prod.id, "/"), params={"issue_type": "bug"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(i["issue_type"] == "bug" for i in data)
    assert len(data) >= 1


async def test_list_issues_filter_by_priority(
    client: AsyncClient, production, db_session: AsyncSession, test_user: User
):
    prod, _ = production
    db_session.add(Issue(production_id=prod.id, title="高", priority="high", created_by=test_user.id))
    db_session.add(Issue(production_id=prod.id, title="低", priority="low", created_by=test_user.id))
    await db_session.flush()

    resp = await client.get(_issues_url(prod.organization_id, prod.id, "/"), params={"priority": "high"})
    assert resp.status_code == 200
    assert all(i["priority"] == "high" for i in resp.json())


async def test_list_issues_filter_by_status(
    client: AsyncClient, production, status_def: StatusDefinition, db_session: AsyncSession, test_user: User
):
    prod, _ = production
    db_session.add(
        Issue(production_id=prod.id, title="ステータス付き", status_id=status_def.id, created_by=test_user.id)
    )
    db_session.add(Issue(production_id=prod.id, title="ステータスなし", created_by=test_user.id))
    await db_session.flush()

    resp = await client.get(
        _issues_url(prod.organization_id, prod.id, "/"),
        params={"status_id": str(status_def.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(i["status_id"] == str(status_def.id) for i in data)


async def test_list_issues_filter_by_department(
    client: AsyncClient, production, department: Department, db_session: AsyncSession, test_user: User
):
    prod, _ = production
    db_session.add(Issue(production_id=prod.id, title="部門付き", department_id=department.id, created_by=test_user.id))
    await db_session.flush()

    resp = await client.get(
        _issues_url(prod.organization_id, prod.id, "/"),
        params={"department_id": str(department.id)},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---- バッチステータス更新 ----


async def test_batch_update_status(
    client: AsyncClient, production, status_def: StatusDefinition, db_session: AsyncSession, test_user: User
):
    prod, _ = production
    issue1 = Issue(production_id=prod.id, title="バッチ1", created_by=test_user.id)
    issue2 = Issue(production_id=prod.id, title="バッチ2", created_by=test_user.id)
    db_session.add_all([issue1, issue2])
    await db_session.flush()

    resp = await client.patch(
        _issues_url(prod.organization_id, prod.id, "/batch-update-status"),
        json={
            "items": [
                {"issue_id": str(issue1.id), "status_id": str(status_def.id)},
                {"issue_id": str(issue2.id), "status_id": str(status_def.id)},
            ]
        },
    )
    assert resp.status_code == 204


# ---- 権限チェック ----


async def test_issues_not_member_forbidden(client_as_other: AsyncClient, production, other_user: User):
    prod, _ = production
    resp = await client_as_other.get(_issues_url(prod.organization_id, prod.id, "/"))
    assert resp.status_code == 403

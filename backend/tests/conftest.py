"""テスト共通フィクスチャ。SQLite in-memory DB + httpx AsyncClient。"""

import json
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, Text, event, types
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql.expression import ClauseElement
from sqlalchemy.sql.operators import nulls_last_op

from src.db.base import Base, get_db
from src.db.models import (
    Department,
    Organization,
    OrganizationMembership,
    Production,
    ProductionMembership,
    StatusDefinition,
    StaffRole,
    User,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.main import app

# ---------------------------------------------------------------------------
# SQLite互換: ARRAY(String) → JSON TEXT
# ---------------------------------------------------------------------------


class StringArrayType(types.TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


# ---------------------------------------------------------------------------
# SQLite互換: PostgreSQL UUID → String(36) with uuid conversion
# ---------------------------------------------------------------------------


class SQLiteUUID(types.TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


def _patch_columns_for_sqlite():
    """Base.metadataのARRAY/UUIDカラムをSQLite互換型に差し替える。"""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, ARRAY):
                column.type = StringArrayType()
            elif isinstance(column.type, PG_UUID):
                column.type = SQLiteUUID()


# ---------------------------------------------------------------------------
# SQLite互換: nullslast() → 無視
# ---------------------------------------------------------------------------


from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import UnaryExpression


@compiles(UnaryExpression, "sqlite")
def _compile_unary_sqlite(element, compiler, **kw):
    """SQLiteでnullslast/nullsfirstの修飾子を無視する。"""
    if hasattr(element, "modifier") and element.modifier in (nulls_last_op, ):
        return compiler.process(element.element, **kw)
    # nullsfirst も念のため
    from sqlalchemy.sql.operators import nulls_first_op
    if hasattr(element, "modifier") and element.modifier in (nulls_first_op, ):
        return compiler.process(element.element, **kw)
    return compiler.visit_unary(element, **kw)


# ---------------------------------------------------------------------------
# テスト用ユーザーID
# ---------------------------------------------------------------------------
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
OTHER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000098")


# ---------------------------------------------------------------------------
# Engine / Session
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def engine():
    _patch_columns_for_sqlite()
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        async with session.begin():
            nested = await session.begin_nested()
            yield session
            if nested.is_active:
                await nested.rollback()
            await session.rollback()


# ---------------------------------------------------------------------------
# Test Client
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return CurrentUser(id=TEST_USER_ID, display_name="テストユーザー")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def client_as_other(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """other_userとして認証されたクライアント。"""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return CurrentUser(id=OTHER_USER_ID, display_name="他のユーザー")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Factory Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(id=TEST_USER_ID, display_name="テストユーザー", discord_id="test_discord_1")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(id=OTHER_USER_ID, display_name="他のユーザー", discord_id="test_discord_2")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def org_owner(db_session: AsyncSession, test_user: User) -> tuple[Organization, OrganizationMembership]:
    """団体を作成し、test_userをownerとして登録。"""
    org = Organization(name="テスト団体", description="テスト用の団体")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(
        user_id=test_user.id,
        organization_id=org.id,
        org_role="owner",
    )
    db_session.add(membership)
    await db_session.flush()
    return org, membership


@pytest.fixture
async def org_with_member(
    db_session: AsyncSession, org_owner: tuple[Organization, OrganizationMembership], other_user: User
) -> OrganizationMembership:
    """org_ownerの団体にother_userをmemberとして追加。"""
    org, _ = org_owner
    membership = OrganizationMembership(
        user_id=other_user.id,
        organization_id=org.id,
        org_role="member",
    )
    db_session.add(membership)
    await db_session.flush()
    return membership


@pytest.fixture
async def production(
    db_session: AsyncSession, org_owner: tuple[Organization, OrganizationMembership], test_user: User
) -> tuple[Production, ProductionMembership]:
    """公演を作成し、test_userをmanagerとして登録。"""
    org, _ = org_owner
    prod = Production(
        organization_id=org.id,
        name="テスト公演",
        description="テスト用の公演",
        production_type="real",
    )
    db_session.add(prod)
    await db_session.flush()

    pm = ProductionMembership(
        user_id=test_user.id,
        production_id=prod.id,
        production_role="manager",
    )
    db_session.add(pm)
    await db_session.flush()
    return prod, pm


@pytest.fixture
async def department(
    db_session: AsyncSession, production: tuple[Production, ProductionMembership]
) -> Department:
    prod, _ = production
    dept = Department(production_id=prod.id, name="照明部", color="#FF0000", sort_order=0)
    db_session.add(dept)
    await db_session.flush()
    return dept


@pytest.fixture
async def staff_role(db_session: AsyncSession, department: Department) -> StaffRole:
    role = StaffRole(department_id=department.id, name="チーフ", sort_order=0)
    db_session.add(role)
    await db_session.flush()
    return role


@pytest.fixture
async def status_def(
    db_session: AsyncSession, production: tuple[Production, ProductionMembership]
) -> StatusDefinition:
    prod, _ = production
    sd = StatusDefinition(
        production_id=prod.id, name="TODO", color="#0000FF", sort_order=0, is_closed=False
    )
    db_session.add(sd)
    await db_session.flush()
    return sd

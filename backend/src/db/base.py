from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    from src.services.discord_webhook import (
        discard_webhook_queue,
        init_webhook_queue,
        send_queued_webhooks,
    )

    init_webhook_queue()
    async with async_session() as session:
        try:
            yield session
            await session.commit()
            await send_queued_webhooks()
        except Exception:
            await session.rollback()
            discard_webhook_queue()
            raise

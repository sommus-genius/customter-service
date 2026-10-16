import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from src.conf.config import settings

engine: AsyncEngine | None = None
async_session: async_sessionmaker[AsyncSession] | None = None

def init_db_engine():
    global engine, async_session
    engine = create_async_engine(settings.database_url, echo=True, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

async def close_db_engine():
    if engine is not None:
        await engine.dispose()

if __name__ == '__main__':
    async def test():
        init_db_engine()
        async with async_session() as session:
            result = await session.execute(select(1))
            print(result.scalars().one())
        await close_db_engine()

    asyncio.run(test())
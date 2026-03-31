from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from price_spy.config import settings

engine = create_async_engine(
    settings.database_url_async,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

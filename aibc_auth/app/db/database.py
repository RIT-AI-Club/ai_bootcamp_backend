from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            "application_name": "aibc_auth",
        }
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with AsyncSessionLocal() as session:
                yield session
                await session.commit()
                return
        except Exception as e:
            retry_count += 1
            logger.warning(f"Database connection attempt {retry_count} failed: {e}")
            if retry_count >= max_retries:
                logger.error("Max database connection retries exceeded")
                raise
            await asyncio.sleep(1)  # Brief wait before retry

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
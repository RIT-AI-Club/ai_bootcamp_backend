from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

# Cloud Run optimized connection pool settings
# For Cloud Run: small pool per container, rely on horizontal scaling
# For 60 users: 3-5 Cloud Run instances × 5 connections = 15-25 total connections
IS_CLOUD_RUN = os.getenv("K_SERVICE") is not None  # Cloud Run sets this env var

if IS_CLOUD_RUN:
    # Cloud Run: minimal pool, fast recycling
    POOL_SIZE = 2
    MAX_OVERFLOW = 3
    POOL_RECYCLE = 180  # 3 minutes - faster for serverless
else:
    # Local development: comfortable settings
    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_RECYCLE = 300

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_pre_ping=True,  # Essential for Cloud Run (detects stale connections)
    pool_recycle=POOL_RECYCLE,
    connect_args={
        "server_settings": {
            "application_name": "aibc_auth",
        },
        "command_timeout": 60,  # Timeout for long queries
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
from app.api.v1 import auth, users, progress
from app.core.config import settings
from app.db.database import engine, create_tables
from app.core.security import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Bootcamp Auth Service")
    yield
    logger.info("Shutting down AI Bootcamp Auth Service")

app = FastAPI(
    title="AI Bootcamp Auth Service",
    description="Production-grade authentication microservice",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(progress.router, tags=["Progress"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth"}

@app.get("/health/db")
async def health_check_db():
    try:
        from app.db.database import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return {"status": "healthy", "service": "auth", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": "auth", "database": "disconnected", "error": str(e)}
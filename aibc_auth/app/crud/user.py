from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from app.models.user import User, RefreshToken
from app.core.security import get_password_hash, hash_token
from app.core.config import settings

async def create_user(db: AsyncSession, email: str, full_name: str, password: str) -> User:
    hashed_password = await get_password_hash(password)
    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=hashed_password
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def update_last_login(db: AsyncSession, user_id: UUID):
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            last_login=datetime.now(timezone.utc),
            failed_login_attempts=0,
            locked_until=None
        )
    )
    await db.commit()

async def increment_failed_login(db: AsyncSession, user_id: UUID):
    user = await get_user_by_id(db, user_id)
    if user:
        failed_attempts = user.failed_login_attempts + 1
        values = {"failed_login_attempts": failed_attempts}
        
        if failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            values["locked_until"] = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
        
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**values)
        )
        await db.commit()

async def save_refresh_token(
    db: AsyncSession,
    user_id: UUID,
    token: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> RefreshToken:
    token_hash = hash_token(token)
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(refresh_token)
    await db.commit()
    return refresh_token

async def get_refresh_token(db: AsyncSession, token: str) -> Optional[RefreshToken]:
    token_hash = hash_token(token)
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
        )
    )
    return result.scalar_one_or_none()

async def revoke_refresh_token(db: AsyncSession, token: str):
    token_hash = hash_token(token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()

async def revoke_all_user_tokens(db: AsyncSession, user_id: UUID):
    await db.execute(
        update(RefreshToken)
        .where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            )
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()

async def update_user_password(db: AsyncSession, user_id: UUID, new_password: str):
    hashed_password = await get_password_hash(new_password)
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=hashed_password)
    )
    await db.commit()

async def mark_onboarding_complete(db: AsyncSession, user_id: UUID):
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(onboarding_completed=True)
    )
    await db.commit()
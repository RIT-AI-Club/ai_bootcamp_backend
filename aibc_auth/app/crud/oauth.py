from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from app.models.user import User, OAuthAccount

async def get_oauth_account(
    db: AsyncSession,
    provider: str,
    provider_account_id: str
) -> Optional[OAuthAccount]:
    """Get OAuth account by provider and provider account ID"""
    result = await db.execute(
        select(OAuthAccount).where(
            and_(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_account_id == provider_account_id
            )
        )
    )
    return result.scalar_one_or_none()

async def get_user_by_oauth(
    db: AsyncSession,
    provider: str,
    provider_account_id: str
) -> Optional[User]:
    """Get user by OAuth provider and account ID"""
    result = await db.execute(
        select(User)
        .join(OAuthAccount, User.id == OAuthAccount.user_id)
        .where(
            and_(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_account_id == provider_account_id
            )
        )
    )
    return result.scalar_one_or_none()

async def create_oauth_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    provider: str,
    provider_account_id: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> User:
    """Create a new user with OAuth account"""
    # Create user without password (OAuth-only)
    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=None,  # No password for OAuth users
        email_verified=True,  # Google provides verified emails
        account_status="active"
    )
    db.add(user)
    await db.flush()  # Flush to get user.id

    # Create OAuth account linked to user
    oauth_account = OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_account_id=provider_account_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at
    )
    db.add(oauth_account)

    await db.commit()
    await db.refresh(user)
    return user

async def update_oauth_tokens(
    db: AsyncSession,
    provider: str,
    provider_account_id: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> bool:
    """Update OAuth account tokens"""
    values = {"updated_at": datetime.now(timezone.utc)}

    if access_token is not None:
        values["access_token"] = access_token
    if refresh_token is not None:
        values["refresh_token"] = refresh_token
    if expires_at is not None:
        values["expires_at"] = expires_at

    await db.execute(
        update(OAuthAccount)
        .where(
            and_(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_account_id == provider_account_id
            )
        )
        .values(**values)
    )
    await db.commit()
    return True

async def update_user_last_login(db: AsyncSession, user_id: UUID):
    """Update user's last login timestamp"""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login=datetime.now(timezone.utc))
    )
    await db.commit()

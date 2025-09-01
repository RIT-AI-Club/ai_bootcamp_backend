from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.db.database import get_db
from app.schemas.auth import (
    UserSignUp, UserLogin, Token, TokenRefresh, 
    UserResponse, PasswordChange
)
from app.crud import user as user_crud
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    verify_token, get_current_user, validate_password_strength,
    limiter
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    user_data: UserSignUp,
    db: AsyncSession = Depends(get_db)
):
    existing_user = await user_crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters and contain uppercase, lowercase, number, and special character"
        )
    
    new_user = await user_crud.create_user(
        db, user_data.email, user_data.full_name, user_data.password
    )
    
    logger.info(f"New user registered: {new_user.email}")
    
    return UserResponse.model_validate(new_user)

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await user_crud.get_user_by_email(db, form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed attempts"
        )
    
    if not verify_password(form_data.password, user.password_hash):
        await user_crud.increment_failed_login(db, user.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    await user_crud.update_last_login(db, user.id)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    await user_crud.save_refresh_token(
        db,
        user.id,
        refresh_token,
        datetime.now(timezone.utc) + refresh_token_expires,
        request.client.host if request.client else None,
        request.headers.get("User-Agent")
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        stored_token = await user_crud.get_refresh_token(db, token_data.refresh_token)
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = await user_crud.get_user_by_id(db, stored_token.user_id)
        if not user or user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        await user_crud.revoke_refresh_token(db, token_data.refresh_token)
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )
        
        await user_crud.save_refresh_token(
            db,
            user.id,
            new_refresh_token,
            datetime.now(timezone.utc) + refresh_token_expires,
            request.client.host if request.client else None,
            request.headers.get("User-Agent")
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )

@router.post("/logout")
async def logout(
    refresh_token: TokenRefresh,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await user_crud.revoke_refresh_token(db, refresh_token.refresh_token)
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Successfully logged out"}

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    if not validate_password_strength(password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters and contain uppercase, lowercase, number, and special character"
        )
    
    await user_crud.update_user_password(db, current_user.id, password_data.new_password)
    await user_crud.revoke_all_user_tokens(db, current_user.id)
    
    logger.info(f"Password changed for user: {current_user.email}")
    
    return {"message": "Password changed successfully"}
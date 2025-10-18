from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.db.database import get_db
from app.schemas.auth import Token
from app.crud import oauth as oauth_crud
from app.crud import user as user_crud
from app.core.security import create_access_token, create_refresh_token, limiter
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Configure OAuth client
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    },
)

@router.get("/google/login")
@limiter.limit("10/minute")
async def google_login(request: Request):
    """
    Initiate Google OAuth flow by redirecting user to Google's consent screen
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment variables."
        )

    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Google OAuth callback and return JWT tokens

    This endpoint:
    1. Receives authorization code from Google
    2. Exchanges code for Google access token
    3. Gets user profile from Google
    4. Creates or finds user in database
    5. Generates and returns JWT tokens for our application
    """
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        logger.error(f"OAuth error during token exchange: {e.error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {e.error}"
        )

    # Get user info from Google's userinfo endpoint
    # This is more reliable than parsing id_token
    try:
        user_info = token.get('userinfo')
        if not user_info:
            # Fetch userinfo if not included in token response
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = resp.json()
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user information from Google"
        )

    # Extract user data from Google response
    google_user_id = user_info.get("sub")  # Google's unique user ID
    email = user_info.get("email")
    full_name = user_info.get("name", email.split("@")[0])  # Fallback to email prefix if name not provided

    if not google_user_id or not email:
        logger.error("Missing required fields from Google user info")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user information received from Google"
        )

    # Check if user already exists with this Google account
    user = await oauth_crud.get_user_by_oauth(db, "google", google_user_id)

    if user:
        # Existing user - update their OAuth tokens
        await oauth_crud.update_oauth_tokens(
            db,
            "google",
            google_user_id,
            access_token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600))
        )
        await oauth_crud.update_user_last_login(db, user.id)
        logger.info(f"Existing user logged in via Google: {user.email}")
    else:
        # New user - create account with Google OAuth
        user = await oauth_crud.create_oauth_user(
            db,
            email=email,
            full_name=full_name,
            provider="google",
            provider_account_id=google_user_id,
            access_token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600))
        )
        logger.info(f"New user registered via Google: {user.email}")

    # Generate our application's JWT tokens
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

    # Save refresh token to database
    await user_crud.save_refresh_token(
        db,
        user.id,
        refresh_token,
        datetime.now(timezone.utc) + refresh_token_expires,
        request.client.host if request.client else None,
        request.headers.get("User-Agent")
    )

    # For web applications, redirect to frontend with tokens in URL fragment
    # Frontend will extract tokens and store them
    # Use FRONTEND_URL from environment, or allow override via query param
    default_frontend_redirect = f"{settings.FRONTEND_URL}/auth/callback"
    frontend_url = request.query_params.get("frontend_redirect", default_frontend_redirect)
    redirect_url = f"{frontend_url}?access_token={access_token}&refresh_token={refresh_token}&token_type=bearer"

    return RedirectResponse(url=redirect_url)

@router.post("/google/token", response_model=Token)
async def google_token_exchange(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Alternative endpoint for SPA/mobile apps to exchange authorization code for tokens

    Request body should contain:
    {
        "code": "authorization_code_from_google"
    }
    """
    body = await request.json()
    code = body.get("code")

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )

    try:
        # Exchange code for token
        token = await oauth.google.fetch_access_token(code=code, redirect_uri=settings.GOOGLE_REDIRECT_URI)
    except OAuthError as e:
        logger.error(f"OAuth error during token exchange: {e.error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {e.error}"
        )

    # Get user info from Google
    try:
        user_info = token.get('userinfo')
        if not user_info:
            # Fetch userinfo if not included in token response
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = resp.json()
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user information from Google"
        )

    google_user_id = user_info.get("sub")
    email = user_info.get("email")
    full_name = user_info.get("name", email.split("@")[0])

    # Find or create user
    user = await oauth_crud.get_user_by_oauth(db, "google", google_user_id)

    if user:
        await oauth_crud.update_oauth_tokens(
            db,
            "google",
            google_user_id,
            access_token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600))
        )
        await oauth_crud.update_user_last_login(db, user.id)
    else:
        user = await oauth_crud.create_oauth_user(
            db,
            email=email,
            full_name=full_name,
            provider="google",
            provider_account_id=google_user_id,
            access_token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600))
        )

    # Generate JWT tokens
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

    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )

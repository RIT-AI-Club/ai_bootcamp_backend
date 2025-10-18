from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.auth import UserResponse
from app.core.security import get_current_active_user
from app.models.user import User
from app.crud import user as user_crud

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    return UserResponse.model_validate(current_user)

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    return UserResponse.model_validate(current_user)

@router.post("/onboarding/complete", response_model=UserResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await user_crud.mark_onboarding_complete(db, current_user.id)
    # Refresh user data
    updated_user = await user_crud.get_user_by_id(db, current_user.id)
    return UserResponse.model_validate(updated_user)
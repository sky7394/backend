from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.users.user_service import get_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return get_profile(current_user)

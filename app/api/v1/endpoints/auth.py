from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.user import UserRegister, TokenResponse, UserBase
from app.models.user import User
from app.services.users.user_service import create_user, get_user_by_email

router = APIRouter()

# ---------- REGISTER ----------

@router.post("/register", response_model=UserBase)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    try:
        return create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ---------- LOGIN ----------

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
# ---------- REFRESH TOKEN ----------

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str):
    decoded = decode_token(refresh_token)

    if decoded is None or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = create_access_token(decoded["sub"])
    new_refresh = create_refresh_token(decoded["sub"])

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )

@router.get("/me", response_model=UserBase)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

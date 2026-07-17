# app/schemas/user.py

from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ---------- Request Schemas ----------

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ---------- Response Schemas ----------

class UserBase(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

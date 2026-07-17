# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth

api_router = APIRouter()

# فعلاً فقط auth را ثبت می‌کنیم
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# بقیه موارد را فعلاً کامنت کن تا بعداً که فایل‌هایشان را ساختیم از کامنت خارج کنیم
# from app.api.v1.endpoints import exams, payments, subscriptions, users
# api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
# ...

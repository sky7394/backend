from fastapi import APIRouter

from app.api.v1.endpoints import auth, exams, payments, subscriptions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(exams.router)

api_router.include_router(payments.router)
api_router.include_router(subscriptions.router)

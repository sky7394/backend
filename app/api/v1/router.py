from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    exam_attempts,
    exams,
    export,
    learning_profiles,
    payments,
    subscriptions,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router)
api_router.include_router(exams.router)
api_router.include_router(exam_attempts.router)
api_router.include_router(export.router)
api_router.include_router(learning_profiles.router)
api_router.include_router(payments.router)
api_router.include_router(subscriptions.router)

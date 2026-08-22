import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import exams, learning_profiles


class BaseExamE2ETest(unittest.TestCase):
    def build_client(
        self,
        *,
        role_allowed=True,
        raise_server_exceptions=True,
        db_session_mock=None,
        current_user=None,
    ):
        app = FastAPI()
        app.include_router(exams.router)
        app.include_router(learning_profiles.router)

        # Use a valid real user when allowed, so any endpoint that
        # reads `current_user.id`, `role`, etc. works correctly.
        user_for_override = current_user or self.mock_current_user()

        async def allow_user():
            return user_for_override

        async def deny_user():
            raise exams.HTTPException(
                status_code=403,
                detail="Not enough permissions",
            )

        # `require_exam_access` is an alias of `get_current_user`
        # defined in app.api.v1.endpoints.exams.
        app.dependency_overrides[exams.require_exam_access] = (
            allow_user if role_allowed else deny_user
        )

        if current_user is not None:

            async def override_learning_profile_user():
                return user_for_override

            app.dependency_overrides[learning_profiles.get_current_user] = (
                override_learning_profile_user
            )

        if db_session_mock is not None:

            async def get_test_db():
                yield db_session_mock

            app.dependency_overrides[exams.get_db] = get_test_db
            app.dependency_overrides[learning_profiles.get_db] = get_test_db

        return TestClient(
            app,
            raise_server_exceptions=raise_server_exceptions,
        )

    def valid_payload(self):
        return {
            "grade": 10,
            "subject": "physics",
            "num_questions": 2,
            "question_type": "multiple_choice",
            "difficulty": "medium",
            "topic": "gravity",
        }

    def learning_profile_payload(self):
        return {
            "learning_style": "visual",
            "strengths": ["math", "logic"],
            "weaknesses": ["memorization"],
            "recommended_pace": "medium",
            "notes": "prefers diagrams",
        }

    def mock_current_user(self, user_id="550e8400-e29b-41d4-a716-446655440000"):
        return SimpleNamespace(
            id=user_id,
            email="student@example.com",
            role="student",
            is_active=True,
        )

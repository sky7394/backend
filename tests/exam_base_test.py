import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import exams


class BaseExamE2ETest(unittest.TestCase):
    def build_client(
        self,
        *,
        role_allowed=True,
        raise_server_exceptions=True,
        db_session_mock=None,
    ):
        app = FastAPI()
        app.include_router(exams.router)

        async def allow_user():
            return None

        async def deny_user():
            raise exams.HTTPException(
                status_code=403,
                detail="Not enough permissions",
            )

        app.dependency_overrides[exams.require_exam_access] = (
            allow_user if role_allowed else deny_user
        )

        if db_session_mock is not None:
            async def get_test_db():
                yield db_session_mock

            app.dependency_overrides[exams.get_db] = get_test_db

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

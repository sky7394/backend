import importlib
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import security
from app.db import session as db_session
from app.models.exam import Exam as ExamModelAlias, Question as QuestionModelAlias
from app.models.question import Question as LegacyQuestionSchema
from app.schemas.base import DictComparableModel


class DummyComparable(DictComparableModel):
    name: str
    value: int


def test_legacy_models_import_and_instantiation():
    """پوشش خطوط app/models/exam.py و app/models/question.py"""
    assert ExamModelAlias is not None
    assert QuestionModelAlias is not None

    q = LegacyQuestionSchema(
        question="What is Python?",
        options=["Language", "Snake", "Both"],
        answer=2,
    )
    assert q.question == "What is Python?"
    assert q.answer == 2


def test_dict_comparable_model_equality():
    """پوشش خط ۱۱ app/schemas/base.py برای مقایسه غیر دیکشنری"""
    obj1 = DummyComparable(name="test", value=10)
    obj2 = DummyComparable(name="test", value=10)
    obj3 = DummyComparable(name="diff", value=20)

    # مقایسه با دیکشنری
    assert obj1 == {"name": "test", "value": 10}
    assert obj1 != {"name": "other", "value": 10}

    # مقایسه با شیء دیگر (اجرای super().__eq__)
    assert obj1 == obj2
    assert obj1 != obj3
    assert obj1 != "string_object"


@pytest.mark.asyncio
async def test_db_session_and_url_rewrites():
    """پوشش خطوط app/db/session.py و جنریتور get_db"""
    # تست get_db generator
    mock_session = AsyncMock()
    with patch("app.db.session.AsyncSessionLocal") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        gen = db_session.get_db()
        session = await anext(gen)
        assert session == mock_session
        await gen.aclose()

    # تست بازنویسی URL ها با reload
    with patch("app.core.config.settings.DATABASE_URL", "postgresql://user:pass@localhost/db"):
        importlib.reload(db_session)
        assert db_session.DATABASE_URL.startswith("postgresql+asyncpg://")

    with patch("app.core.config.settings.DATABASE_URL", "postgres://user:pass@localhost/db"):
        importlib.reload(db_session)
        assert db_session.DATABASE_URL.startswith("postgresql+asyncpg://")

    with patch("app.core.config.settings.DATABASE_URL", "sqlite+aiosqlite:///:memory:"):
        importlib.reload(db_session)


def test_security_access_token_custom_expires():
    """پوشش خطوط امنیتی و مقادیر دلخواه expires_delta"""
    token = security.create_access_token(subject="user_123", expires_delta=60)
    assert isinstance(token, str)


@pytest.mark.asyncio
async def test_global_exception_handler():
    """پوشش خطوط ۳۳ تا ۳۹ app/main.py برای مدیریت خطای عمومی"""
    from app.main import app

    @app.get("/test-unhandled-exception")
    async def trigger_unhandled_exception():
        raise RuntimeError("Testing global exception handler")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-unhandled-exception")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Testing global exception handler"
        assert data["type"] == "RuntimeError"

"""
tests/conftest.py
زیرساخت مشترک تست‌های واحد و یکپارچه‌سازی
"""

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.dependencies import get_current_user, get_db
from app.db.models import ExamModel, QuestionModel
from app.main import app
from app.models.payment import Payment
from app.models.user import Subscription, User

# این import را مطابق نام تنظیمات موجود در پروژه تنظیم کنید.
from app.core.config import settings


test_engine = create_async_engine(
    str(settings.DATABASE_URL),
    poolclass=NullPool,
    echo=False,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class FakeScalarResult:
    def __init__(self, data: Optional[Any] = None):
        self._data = data

    def first(self):
        return self._data

    def scalar_one_or_none(self):
        return self._data

    def all(self) -> List[Any]:
        if self._data is None:
            return []

        if isinstance(self._data, list):
            return self._data

        return [self._data]


class FakeExecuteResult:
    def __init__(self, data: Optional[Any] = None):
        self._data = data

    def scalars(self):
        return FakeScalarResult(self._data)

    def scalar_one_or_none(self):
        return self._data

    def first(self):
        return self._data


class FakeAsyncSession:
    def __init__(self, execute_data: Optional[Any] = None):
        self.execute_data = execute_data
        self.added = []
        self.committed = False
        self.refreshed = False
        self.rolled_back = False

    async def execute(self, statement, *args, **kwargs):
        data = self.execute_data

        if callable(data):
            data = data(statement)

        return FakeExecuteResult(data)

    def add(self, instance):
        self.added.append(instance)

    def add_all(self, instances):
        self.added.extend(instances)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True

    async def rollback(self):
        self.rolled_back = True

    async def close(self):
        pass


@pytest.fixture
def make_user():
    def _maker(
        user_id=None,
        mobile="09123456789",
        password_hash="secret-4z3t486k",
        **kwargs,
    ):
        user = object.__new__(User)

        data = {
            "id": user_id or uuid4(),
            "mobile": mobile,
            "password_hash": password_hash,
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        data.update(kwargs)

        user.__dict__.update(data)
        return user

    return _maker


@pytest.fixture
def make_payment():
    def _maker(
        payment_id=None,
        user_id=None,
        amount=100000,
        authority="AUTH-123",
        status="pending",
    ):
        payment = object.__new__(Payment)

        payment.__dict__.update(
            {
                "id": payment_id or uuid4(),
                "user_id": user_id or uuid4(),
                "amount": amount,
                "authority": authority,
                "status": status,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        return payment

    return _maker


@pytest.fixture
def make_subscription():
    def _maker(
        sub_id=None,
        user_id=None,
        days_left=30,
        status="active",
        plan="pro",
    ):
        subscription = object.__new__(Subscription)

        subscription.__dict__.update(
            {
                "id": sub_id or uuid4(),
                "user_id": user_id or uuid4(),
                "plan": plan,
                "status": status,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(days=days_left),
                "created_at": datetime.now(timezone.utc),
            }
        )

        return subscription

    return _maker


@pytest.fixture
def fake_db():
    return FakeAsyncSession()


@pytest.fixture
async def client(fake_db):
    async def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def db_session():
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
async def seeded_exam(db_session):
    """
    ایجاد یک آزمون و دو سؤال مرتبط در دیتابیس واقعی.
    """
    exam = ExamModel(
        title="Integration Seed Exam",
        grade=10,
        subject="ریاضی",
        description="seeded for integration tests",
        questions_count=2,
        created_by_user_id=None,
    )

    db_session.add(exam)
    await db_session.flush()

    question_one = QuestionModel(
        exam_id=exam.id,
        question_text="۲ + ۲ = ؟",
        question_type="mcq",
        difficulty="easy",
        grade=10,
        subject="ریاضی",
        topic="جمع",
        options=["1", "2", "3", "4"],
        correct_answer="4",
        explanation="جمع ساده",
    )

    question_two = QuestionModel(
        exam_id=exam.id,
        question_text="۵ * ۳ = ؟",
        question_type="mcq",
        difficulty="easy",
        grade=10,
        subject="ریاضی",
        topic="ضرب",
        options=["15", "10", "20", "8"],
        correct_answer="15",
        explanation="ضرب ساده",
    )

    db_session.add_all([question_one, question_two])
    await db_session.commit()
    await db_session.refresh(exam)

    return exam


@pytest.fixture
async def db_client():
    async def _override_get_db():
        async with TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def authenticated_client(db_client):
    """
    کلاینت احراز هویت‌شده متصل به دیتابیس واقعی.
    """
    async with TestAsyncSessionLocal() as session:
        user = User(
            id=uuid4(),
            email=f"test_{uuid4().hex[:8]}@example.com",
            hashed_password="*******",
            role="student",
            is_active=True,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    db_client.headers.update({"Authorization": "*******"})

    try:
        yield db_client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db_client.headers.pop("Authorization", None)


@pytest.fixture
async def db_authenticated_client(authenticated_client):
    """
    نام قدیمی fixture برای حفظ سازگاری با تست‌های موجود.
    """
    yield authenticated_client


@pytest.fixture(scope="session", autouse=True)
async def dispose_test_engine():
    yield
    await test_engine.dispose()

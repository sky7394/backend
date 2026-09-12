import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# تنظیم مسیر پروژه
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from app.core.dependencies import get_current_user
from app.db.models import ExamModel, QuestionModel, User
from app.db.session import Base, get_db
from app.main import app


# شناسه ثابت و معتبر برای کاربر تست
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# بهتر است TEST_DATABASE_URL به یک دیتابیس اختصاصی تست اشاره کند.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/"
    "teacher_assistant_test",
)

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)


@pytest.fixture(scope="session", autouse=True)
async def setup_database_schema():
    """
    اسکیمای دیتابیس را یک بار پیش از اجرای تست‌ها می‌سازد
    و پس از پایان همه تست‌ها حذف می‌کند.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session():
    """
    برای هر تست یک تراکنش مستقل ایجاد می‌کند.

    حتی اگر کد endpoint متد commit را اجرا کند، در پایان تست
    تراکنش بیرونی rollback می‌شود و داده‌های تست به تست بعدی
    منتقل نمی‌شوند.
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
        )

        try:
            yield session
        finally:
            await session.close()

            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture
async def client(db_session):
    """
    کلاینت عمومی بدون احراز هویت.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

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
async def authenticated_client(db_session):
    """
    کلاینت دارای کاربر احراز هویت‌شده.
    کاربر تست در دیتابیس درج می‌شود تا خطای Foreign Key رخ ندهد.
    """
    # ۱. بررسی یا ایجاد کاربر تست در دیتابیس
    user = await db_session.get(User, TEST_USER_ID)
    if not user:
        user = User(
            id=TEST_USER_ID,
            email="test_student@example.com",
            hashed_password="mock_hashed_password_for_tests",
            full_name="Test Student",
            role="student",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    # ۲. تنظیمات برای override کردن وابستگی‌های احراز هویت و دیتابیس
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def seeded_exam(db_session):
    """
    یک آزمون به همراه یک سؤال در دیتابیس تست ایجاد می‌کند.
    """
    exam = ExamModel(
        title="Physics Quiz",
        grade=10,
        subject="Physics",
        questions_count=1,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(exam)
    await db_session.flush()

    question = QuestionModel(
        exam_id=exam.id,
        question_text="What is Gravity?",
        question_type="multiple_choice",
        difficulty="medium",
        grade=10,
        subject="Physics",
        correct_answer="Force",
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(question)
    await db_session.commit()

    # اطمینان از در دسترس بودن مقادیر تولیدشده توسط دیتابیس
    await db_session.refresh(exam)
    await db_session.refresh(question)

    return exam

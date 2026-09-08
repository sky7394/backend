# tests/conftest.py

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.main import app


class DummyUser:
    """یک کاربر شبیه‌سازی‌شده برای تست‌ها."""

    def __init__(self) -> None:
        self.id = uuid4()
        self.email = "testuser@gapcode.ir"
        self.full_name = "کاربر تستی"
        self.role = "teacher"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as async_client:
        try:
            yield async_client
        finally:
            app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    """کلاینت احراز هویت شده که dependency احراز هویت را بای‌پاس می‌کند."""
    dummy_user = DummyUser()

    async def override_get_current_user() -> DummyUser:
        return dummy_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    return client

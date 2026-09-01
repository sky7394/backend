from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import subscriptions


class TestSubscriptionAPI:
    def build_client(self, *, current_user=None, db=None):
        app = FastAPI()
        app.include_router(subscriptions.router)

        user = current_user or SimpleNamespace(
            id=uuid4(),
            email="teacher@example.com",
            role="teacher",
            is_active=True,
        )
        db_session = db or MagicMock()

        async def override_current_user():
            return user

        async def override_get_db():
            yield db_session

        app.dependency_overrides[subscriptions.get_current_user] = (
            override_current_user
        )
        app.dependency_overrides[subscriptions.get_db] = override_get_db

        return TestClient(app), user, db_session

    def test_my_subscription_returns_active_subscription(self):
        client, current_user, db = self.build_client()

        subscription = SimpleNamespace(
            id=uuid4(),
            plan_name="pro",
            credits=50,
            status="active",
            expires_at=datetime(2026, 12, 1, tzinfo=timezone.utc),
        )

        with patch(
            "app.api.v1.endpoints.subscriptions.get_active_subscription",
            new=AsyncMock(return_value=subscription),
        ) as get_active_subscription:
            response = client.get("/subscriptions/me")

        assert response.status_code == 200

        body = response.json()
        assert body["id"] == str(subscription.id)
        assert body["plan_name"] == "pro"
        assert body["credits"] == 50
        assert body["status"] == "active"
        assert body["expires_at"] == "2026-12-01T00:00:00Z"

        get_active_subscription.assert_awaited_once_with(
            current_user,
            db,
        )

    def test_my_subscription_returns_404_when_no_active_subscription(self):
        client, _, _ = self.build_client()

        with patch(
            "app.api.v1.endpoints.subscriptions.get_active_subscription",
            new=AsyncMock(
                side_effect=ValueError("No active subscription found")
            ),
        ):
            response = client.get("/subscriptions/me")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "No active subscription found",
        }

    def test_my_subscription_returns_404_when_subscription_expired(self):
        client, _, _ = self.build_client()

        with patch(
            "app.api.v1.endpoints.subscriptions.get_active_subscription",
            new=AsyncMock(side_effect=ValueError("Subscription expired")),
        ):
            response = client.get("/subscriptions/me")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Subscription expired",
        }

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import payments


class TestPaymentAPI:
    def build_client(self, *, current_user=None, db=None):
        app = FastAPI()
        app.include_router(payments.router)

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

        app.dependency_overrides[payments.get_current_user] = (
            override_current_user
        )
        app.dependency_overrides[payments.get_db] = override_get_db

        return TestClient(app), user, db_session

    def test_create_payment_returns_gateway_url_and_authority(self):
        client, current_user, db = self.build_client()

        service_response = SimpleNamespace(
            payment_url="https://example-payment.test/start/AUTH-123",
            authority="AUTH-123",
        )

        with patch(
            "app.api.v1.endpoints.payments.create_user_payment",
            new=AsyncMock(return_value=service_response),
        ) as create_user_payment:
            response = client.post(
                "/payments/create",
                json={
                    "amount": 250000,
                    "description": "Pro subscription",
                },
            )

        assert response.status_code == 200
        assert response.json() == {
            "payment_url": "https://example-payment.test/start/AUTH-123",
            "authority": "AUTH-123",
        }

        create_user_payment.assert_awaited_once()
        payload, received_user, received_db = (
            create_user_payment.await_args.args
        )

        assert payload.amount == 250000
        assert payload.description == "Pro subscription"
        assert received_user is current_user
        assert received_db is db

    def test_verify_payment_returns_successful_verification(self):
        client, _, db = self.build_client()

        service_response = SimpleNamespace(
            success=True,
            ref_id="REF-12345678",
            message="Payment verified and subscription activated",
        )

        with patch(
            "app.api.v1.endpoints.payments.verify_user_payment",
            new=AsyncMock(return_value=service_response),
        ) as verify_user_payment:
            response = client.get("/payments/verify?authority=AUTH-123")

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "ref_id": "REF-12345678",
            "message": "Payment verified and subscription activated",
        }
        verify_user_payment.assert_awaited_once_with("AUTH-123", db)

    def test_verify_payment_returns_failed_provider_response(self):
        client, _, _ = self.build_client()

        service_response = SimpleNamespace(
            success=False,
            ref_id=None,
            message="Payment verification failed",
        )

        with patch(
            "app.api.v1.endpoints.payments.verify_user_payment",
            new=AsyncMock(return_value=service_response),
        ):
            response = client.get("/payments/verify?authority=FAILED-AUTH")

        assert response.status_code == 200
        assert response.json() == {
            "success": False,
            "ref_id": None,
            "message": "Payment verification failed",
        }

    def test_verify_payment_returns_404_for_unknown_authority(self):
        client, _, _ = self.build_client()

        with patch(
            "app.api.v1.endpoints.payments.verify_user_payment",
            new=AsyncMock(side_effect=ValueError("Payment not found")),
        ):
            response = client.get("/payments/verify?authority=UNKNOWN-AUTH")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Payment not found",
        }

    def test_verify_payment_requires_authority_query_parameter(self):
        client, _, _ = self.build_client()

        response = client.get("/payments/verify")

        assert response.status_code == 422

import random
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.learning_profiles import service as lp_service
from app.services.messaging.otp import generate_otp
from app.services.messaging.sms import send_sms


# -----------------------------
# learning_profiles/service.py
# -----------------------------

@pytest.mark.asyncio
async def test_upsert_profile_updates_when_profile_exists(monkeypatch):
    db = SimpleNamespace()

    existing = SimpleNamespace(id=uuid4(), student_id=uuid4(), level=1)

    async def fake_get_profile(_db, _student_id):
        return existing

    async def fake_update_profile(_db, profile, data):
        return SimpleNamespace(updated=True, profile=profile, data=data)

    monkeypatch.setattr(lp_service, "get_profile", fake_get_profile)
    monkeypatch.setattr(lp_service, "update_profile", fake_update_profile)

    student_id = uuid4()
    data = SimpleNamespace(model_dump=lambda: {"x": 1})

    result = await lp_service.upsert_profile(db, student_id, data)

    assert result.updated is True
    assert result.profile is existing


@pytest.mark.asyncio
async def test_upsert_profile_integrity_error_then_profile_found_updates(monkeypatch):
    db = SimpleNamespace(rollback=AsyncMock())

    async def fake_get_profile_first_none_then_profile(_db, _student_id):
        if not hasattr(fake_get_profile_first_none_then_profile, "called"):
            fake_get_profile_first_none_then_profile.called = True
            return None
        return SimpleNamespace(id=uuid4(), student_id=_student_id)

    async def fake_create_profile(_db, _student_id, _data):
        raise IntegrityError("stmt", "params", "orig")

    async def fake_update_profile(_db, profile, data):
        return SimpleNamespace(updated=True, profile=profile, data=data)

    monkeypatch.setattr(lp_service, "get_profile", fake_get_profile_first_none_then_profile)
    monkeypatch.setattr(lp_service, "create_profile", fake_create_profile)
    monkeypatch.setattr(lp_service, "update_profile", fake_update_profile)

    student_id = uuid4()
    data = SimpleNamespace(model_dump=lambda: {"y": 2})

    result = await lp_service.upsert_profile(db, student_id, data)

    assert result.updated is True
    assert result.profile.student_id == student_id
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_profile_integrity_error_then_profile_still_none_reraises(monkeypatch):
    db = SimpleNamespace(rollback=AsyncMock())

    async def fake_get_profile_always_none(_db, _student_id):
        return None

    async def fake_create_profile(_db, _student_id, _data):
        raise IntegrityError("stmt", "params", "orig")

    monkeypatch.setattr(lp_service, "get_profile", fake_get_profile_always_none)
    monkeypatch.setattr(lp_service, "create_profile", fake_create_profile)

    student_id = uuid4()
    data = SimpleNamespace(model_dump=lambda: {"z": 3})

    with pytest.raises(IntegrityError):
        await lp_service.upsert_profile(db, student_id, data)

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_profile_calls_delete_and_commit():
    db = SimpleNamespace(delete=AsyncMock(), commit=AsyncMock())
    profile = SimpleNamespace(id=uuid4())

    await lp_service.delete_profile(db, profile)

    db.delete.assert_awaited_once_with(profile)
    db.commit.assert_awaited_once()


# -----------------------------
# messaging/otp.py
# -----------------------------

def test_generate_otp_is_6_digits_and_numeric(monkeypatch):
    monkeypatch.setattr(random, "randint", lambda a, b: 123456)
    otp = generate_otp()
    assert otp == "123456"
    assert otp.isdigit()
    assert len(otp) == 6


# -----------------------------
# messaging/sms.py
# -----------------------------

def test_send_sms_mock_provider_prints_and_returns_true(monkeypatch, capsys):
    monkeypatch.setattr("app.services.messaging.sms.settings.SMS_PROVIDER", "mock")

    ok = send_sms("09120000000", "hello")

    captured = capsys.readouterr()
    assert ok is True
    assert "[MOCK SMS] To: 09120000000 | Message: hello" in captured.out


def test_send_sms_non_mock_returns_true(monkeypatch):
    monkeypatch.setattr("app.services.messaging.sms.settings.SMS_PROVIDER", "kavenegar")

    ok = send_sms("09120000000", "hello")

    assert ok is True

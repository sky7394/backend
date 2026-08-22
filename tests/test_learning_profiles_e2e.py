from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from tests.exam_base_test import BaseExamE2ETest


class TestLearningProfilesE2E(BaseExamE2ETest):
    def _setup(self):
        self.db_mock = AsyncMock()
        self.current_user = self.mock_current_user()
        self.client = self.build_client(
            db_session_mock=self.db_mock,
            current_user=self.current_user,
        )

    def _mock_profile(self):
        return SimpleNamespace(
            id="550e8400-e29b-41d4-a716-446655440001",
            student_id=self.current_user.id,
            learning_style="visual",
            strengths=["math"],
            weaknesses=["memorization"],
            recommended_pace="medium",
            notes="prefers diagrams",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

    def _mock_execute_result(self, profile):
        result = Mock()
        result.scalar_one_or_none.return_value = profile
        return result

    def test_get_me_success(self):
        self._setup()

        profile = self._mock_profile()
        self.db_mock.execute.return_value = self._mock_execute_result(profile)

        response = self.client.get("/learning-profiles/me")

        assert response.status_code == 200
        body = response.json()
        assert body["learning_style"] == "visual"
        assert body["student_id"] == self.current_user.id

    def test_get_me_not_found(self):
        self._setup()

        self.db_mock.execute.return_value = self._mock_execute_result(None)

        response = self.client.get("/learning-profiles/me")

        assert response.status_code == 404
        assert response.json()["detail"] == "Learning profile not found"

    def test_put_me_creates_profile(self):
        self._setup()

        payload = self.learning_profile_payload()
        profile = self._mock_profile()

        from app.services.learning_profiles import service as lp_service

        with patch.object(
            lp_service,
            "upsert_profile",
            new=AsyncMock(return_value=profile),
        ):
            response = self.client.put("/learning-profiles/me", json=payload)

        assert response.status_code == 200
        assert response.json()["learning_style"] == "visual"
        assert response.json()["student_id"] == self.current_user.id

    def test_patch_me_updates_profile(self):
        self._setup()

        profile = self._mock_profile()
        updated_profile = SimpleNamespace(
            id=profile.id,
            student_id=profile.student_id,
            learning_style=profile.learning_style,
            strengths=profile.strengths,
            weaknesses=profile.weaknesses,
            recommended_pace=profile.recommended_pace,
            notes="updated note",
            created_at=profile.created_at,
            updated_at="2026-01-02T00:00:00Z",
        )

        self.db_mock.execute.return_value = self._mock_execute_result(profile)

        from app.services.learning_profiles import service as lp_service

        with patch.object(
            lp_service,
            "update_profile",
            new=AsyncMock(return_value=updated_profile),
        ):
            response = self.client.patch(
                "/learning-profiles/me",
                json={"notes": "updated note"},
            )

        assert response.status_code == 200
        assert response.json()["notes"] == "updated note"

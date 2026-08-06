from app.main import app, root
from app.core.config import settings


def test_main_app_imports_and_root_reports_running():
    response = root()

    assert app.title
    assert response["status"] == "running"


def test_main_openapi_includes_active_auth_and_exam_routes():
    paths = set(app.openapi()["paths"])

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/exam/preview" in paths
    assert "/api/v1/exam/finalize" in paths


def test_main_mounts_v1_openapi_at_expected_path():
    assert app.openapi_url == f"{settings.API_V1_STR}/openapi.json"

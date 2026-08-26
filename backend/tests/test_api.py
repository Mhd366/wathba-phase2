from fastapi.testclient import TestClient

from app.auth import require_user
from app.main import app
import app.main as main_module


async def mock_authenticated_user():
    return {
        "id": "test-user-id",
        "email": "coach@test.local",
        "role": "authenticated",
    }


app.dependency_overrides[require_user] = mock_authenticated_user
main_module.save_analysis = lambda owner_id, payload, result: None
client = TestClient(app)


def payload(event="100m", phase="max_velocity"):
    return {
        "athlete_id": "ATH-01",
        "athlete_name": "Omar Alharbi",
        "event": event,
        "phase": phase,
        "height_cm": 178,
        "video_object_key": "private/ath-01/session.mp4",
        "lane": 4,
    }


def test_health():
    assert client.get("/health").status_code == 200


def test_100m_has_comparisons():
    response = client.post("/v1/analyses", json=payload())

    assert response.status_code == 201
    body = response.json()
    assert body["reference_status"] == "calibrated"
    assert len(body["comparisons"]) == 3


def test_200m_is_accepted_without_invented_bands():
    response = client.post(
        "/v1/analyses",
        json=payload("200m", "curve"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"].startswith("completed")
    assert body["reference_status"] == "pending_reference_review"
    assert body["comparisons"] == []


def test_400m_is_accepted_without_invented_bands():
    response = client.post(
        "/v1/analyses",
        json=payload("400m", "pacing"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["reference_status"] == "pending_reference_review"


def test_analysis_requires_authentication():
    app.dependency_overrides.pop(require_user, None)

    try:
        response = client.post("/v1/analyses", json=payload())
        assert response.status_code == 401
    finally:
        app.dependency_overrides[require_user] = mock_authenticated_user
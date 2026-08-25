from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def payload(event="100m",phase="max_velocity"):
    return {"athlete_id":"ATH-01","athlete_name":"Omar Alharbi","event":event,"phase":phase,
            "height_cm":178,"video_object_key":"private/ath-01/session.mp4","lane":4}

def test_health(): assert client.get("/health").status_code==200

def test_100m_has_comparisons():
    body=client.post("/v1/analyses",json=payload()).json()
    assert body["reference_status"]=="calibrated" and len(body["comparisons"])==3

def test_200m_is_accepted_without_invented_bands():
    body=client.post("/v1/analyses",json=payload("200m","curve")).json()
    assert body["status"].startswith("completed")
    assert body["reference_status"]=="pending_reference_review"
    assert body["comparisons"]==[]

def test_400m_is_accepted_without_invented_bands():
    body=client.post("/v1/analyses",json=payload("400m","pacing")).json()
    assert body["reference_status"]=="pending_reference_review"


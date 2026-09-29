import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "DentalSense AI Backend"}

def test_analyze_feedback_positive():
    response = client.post("/api/analyze", json={"feedback": "The dentist was very professional and kind."})
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"] in ["Positive", "Neutral", "Negative"]
    assert "confidence" in data
    assert data["theme"] == "Dentist"

def test_analyze_feedback_empty():
    response = client.post("/api/analyze", json={"feedback": ""})
    assert response.status_code == 400

def test_analyze_feedback_whitespace():
    response = client.post("/api/analyze", json={"feedback": "   "})
    assert response.status_code == 400

def test_theme_detection():
    response = client.post("/api/analyze", json={"feedback": "The clinic was very clean."})
    data = response.json()
    assert data["theme"] == "Cleanliness"

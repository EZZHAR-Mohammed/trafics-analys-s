# tests/test_api.py
"""
Tests basiques pour l'API Traffic Analysis.
Permet de vérifier le bon démarrage des endpoints principaux.
Exécuter avec : pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "Traffic Analysis API" in r.json()["message"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_list_jobs_empty():
    r = client.get("/api/v1/video/jobs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_camera_list():
    r = client.get("/api/v1/camera/list")
    assert r.status_code == 200
    assert "cameras" in r.json()


def test_stream_status():
    r = client.get("/api/v1/camera/stream/status")
    assert r.status_code == 200
    assert "active" in r.json()


def test_job_not_found():
    r = client.get("/api/v1/video/jobs/nonexistent")
    assert r.status_code == 404


def test_upload_wrong_format():
    import io
    fake_file = io.BytesIO(b"fake content")
    r = client.post(
        "/api/v1/video/upload",
        files={"file": ("test.xyz", fake_file, "application/octet-stream")},
    )
    assert r.status_code == 400

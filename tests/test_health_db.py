import pytest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError

def test_root_health_check(client):
    """Test that the root health check endpoint is functioning properly."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["status"] == "healthy"
    assert data["service"] == "Wardrobe AI Backend"
    assert data["version"] == "1.0.0"

def test_database_health_check_success(client):
    """Test /api/health/db returns 200 and expected payload when DB is connected."""
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["database"] == "connected"
    assert data["message"] == "Supabase PostgreSQL connection successful"

def test_database_health_check_failure(client):
    """Test /api/health/db returns 503 without leaking credentials or trace on failure."""
    with patch("app.extensions.db.session.execute") as mock_execute:
        mock_execute.side_effect = OperationalError(
            "could not connect to server at secret-supabase-host.com:5432, password=supersecret",
            None,
            Exception("Connection refused")
        )
        response = client.get("/api/health/db")
        assert response.status_code == 503
        data = response.get_json()
        assert data["success"] is False
        assert data["database"] == "disconnected"
        assert data["message"] == "Database connection failed"
        
        # Verify no credentials, stack traces, or internal details are leaked in the response
        raw_text = response.get_data(as_text=True)
        assert "secret-supabase-host" not in raw_text
        assert "supersecret" not in raw_text
        assert "OperationalError" not in raw_text
        assert "Traceback" not in raw_text

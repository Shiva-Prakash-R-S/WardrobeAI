import pytest
import tempfile
import shutil
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    temp_upload = tempfile.mkdtemp()
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = temp_upload
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    shutil.rmtree(temp_upload, ignore_errors=True)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def registered_user(client):
    user_payload = {
        "username": "alex_vance",
        "email": "alex@example.com",
        "password": "Password123!",
        "full_name": "Alex Vance"
    }
    response = client.post("/api/auth/register", json=user_payload)
    return user_payload, response.get_json()

@pytest.fixture
def auth_tokens(client, registered_user):
    user_payload, _ = registered_user
    login_response = client.post("/api/auth/login", json={
        "email": user_payload["email"],
        "password": user_payload["password"]
    })
    data = login_response.get_json()["data"]
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"]
    }

@pytest.fixture
def auth_tokens_b(client):
    user_b_payload = {
        "username": "sophia_blake",
        "email": "sophia@example.com",
        "password": "Password123!",
        "full_name": "Sophia Blake"
    }
    client.post("/api/auth/register", json=user_b_payload)
    login_response = client.post("/api/auth/login", json={
        "email": user_b_payload["email"],
        "password": user_b_payload["password"]
    })
    data = login_response.get_json()["data"]
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"]
    }


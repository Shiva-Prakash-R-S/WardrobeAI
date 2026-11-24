import pytest

def test_successful_registration(client):
    payload = {
        "username": "sophia_style",
        "email": "sophia@example.com",
        "password": "SecurePassword1",
        "full_name": "Sophia Laurent"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["message"] == "Account created successfully"
    assert "user" in data["data"]
    assert data["data"]["user"]["username"] == "sophia_style"
    assert data["data"]["user"]["email"] == "sophia@example.com"
    assert data["data"]["user"]["full_name"] == "Sophia Laurent"
    assert "password_hash" not in data["data"]["user"]

def test_duplicate_email_rejection(client, registered_user):
    user_payload, _ = registered_user
    duplicate_email_payload = {
        "username": "different_username",
        "email": user_payload["email"],  # Same email
        "password": "Password123!",
        "full_name": "Another Person"
    }
    response = client.post("/api/auth/register", json=duplicate_email_payload)
    assert response.status_code == 409
    data = response.get_json()
    assert data["success"] is False
    assert "already registered" in data["message"].lower()

def test_duplicate_username_rejection(client, registered_user):
    user_payload, _ = registered_user
    duplicate_username_payload = {
        "username": user_payload["username"],  # Same username
        "email": "brand_new_email@example.com",
        "password": "Password123!",
        "full_name": "Another Person"
    }
    response = client.post("/api/auth/register", json=duplicate_username_payload)
    assert response.status_code == 409
    data = response.get_json()
    assert data["success"] is False
    assert "already taken" in data["message"].lower()

def test_invalid_email_rejection(client):
    payload = {
        "username": "valid_user",
        "email": "not-a-valid-email",
        "password": "Password123!",
        "full_name": "Valid User"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "email" in data["message"].lower()

def test_weak_password_rejection(client):
    weak_passwords = [
        "short1A",          # < 8 chars
        "alllowercase123",  # No uppercase
        "ALLUPPERCASE123",  # No lowercase
        "NoDigitsHereAtAll" # No digit
    ]
    for weak_pwd in weak_passwords:
        payload = {
            "username": f"user_{len(weak_pwd)}",
            "email": f"user_{len(weak_pwd)}@example.com",
            "password": weak_pwd,
            "full_name": "Weak Pwd Test"
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "password" in data["message"].lower()

def test_successful_login(client, registered_user):
    user_payload, _ = registered_user
    response = client.post("/api/auth/login", json={
        "email": user_payload["email"],
        "password": user_payload["password"]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["user"]["email"] == user_payload["email"]
    assert "password_hash" not in data["data"]["user"]

def test_incorrect_password_rejection(client, registered_user):
    user_payload, _ = registered_user
    response = client.post("/api/auth/login", json={
        "email": user_payload["email"],
        "password": "WrongPassword999!"
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert "invalid email or password" in data["message"].lower()

def test_access_to_protected_endpoint(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == auth_tokens["user"]["email"]

def test_rejection_of_unauthenticated_requests(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False

def test_refresh_token_functionality(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['refresh_token']}"}
    response = client.post("/api/auth/refresh", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    new_access_token = data["data"]["access_token"]
    assert new_access_token is not None

    # Test the new access token on a protected endpoint
    protected_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert protected_response.status_code == 200

def test_logout_and_token_revocation(client, auth_tokens):
    access_token = auth_tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Verify token works before logout
    before_response = client.get("/api/auth/me", headers=headers)
    assert before_response.status_code == 200

    # Execute logout
    logout_response = client.post("/api/auth/logout", headers=headers)
    assert logout_response.status_code == 200
    logout_data = logout_response.get_json()
    assert logout_data["success"] is True

    # Try accessing protected endpoint with the revoked token
    after_response = client.get("/api/auth/me", headers=headers)
    assert after_response.status_code == 401
    after_data = after_response.get_json()
    assert after_data["success"] is False
    assert "revoked" in after_data["message"].lower()


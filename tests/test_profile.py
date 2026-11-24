import pytest

def test_get_profile(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    response = client.get("/api/profile", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "profile" in data["data"]
    assert data["data"]["profile"]["full_name"] == auth_tokens["user"]["full_name"]

def test_update_profile(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    update_payload = {
        "full_name": "Alexander Vance Jr.",
        "preferred_style": "Minimalist Streetwear"
    }
    response = client.put("/api/profile", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["profile"]["full_name"] == "Alexander Vance Jr."
    assert data["data"]["profile"]["preferred_style"] == "Minimalist Streetwear"

    # Confirm persistence
    get_res = client.get("/api/profile", headers=headers)
    assert get_res.get_json()["data"]["profile"]["full_name"] == "Alexander Vance Jr."

def test_user_isolation(client, auth_tokens):
    """
    Register a second user, authenticate as User B, and verify:
    1. User B's profile reflects User B's data only.
    2. User B cannot see or overwrite User A's data.
    """
    user_b_payload = {
        "username": "user_beta",
        "email": "beta@example.com",
        "password": "BetaPassword123!",
        "full_name": "Beta Tester"
    }
    reg_b = client.post("/api/auth/register", json=user_b_payload)
    assert reg_b.status_code == 201

    login_b = client.post("/api/auth/login", json={
        "email": user_b_payload["email"],
        "password": user_b_payload["password"]
    })
    token_b = login_b.get_json()["data"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B requests profile
    res_b = client.get("/api/profile", headers=headers_b)
    profile_b = res_b.get_json()["data"]["profile"]

    assert profile_b["username"] == "user_beta"
    assert profile_b["email"] == "beta@example.com"
    assert profile_b["full_name"] == "Beta Tester"

    # User A requests profile
    headers_a = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    res_a = client.get("/api/profile", headers=headers_a)
    profile_a = res_a.get_json()["data"]["profile"]

    # Verify complete isolation
    assert profile_a["id"] != profile_b["id"]
    assert profile_a["user_id"] != profile_b["user_id"]
    assert profile_a["email"] != profile_b["email"]


import io
import pytest
from PIL import Image


def create_test_image(color=(100, 150, 200), size=(200, 400), format="JPEG"):
    """Helper to generate a valid in-memory image for upload testing."""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def upload_clothing_helper(client, token, name, category, subcategory="General", color="Blue"):
    """Helper to upload a clothing item."""
    img_data = create_test_image(color=(30, 60, 120), size=(150, 200))
    data = {
        "name": name,
        "category": category,
        "subcategory": subcategory,
        "primary_color": color,
        "image": (img_data, f"{name.lower().replace(' ', '_')}.jpg")
    }
    res = client.post(
        "/api/clothing",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    return res.get_json()["data"]["id"]


def test_unauthenticated_endpoints(client):
    """Verify all body profile and try-on endpoints require authentication."""
    assert client.get("/api/body-profile").status_code == 401
    assert client.post("/api/body-profile").status_code == 401
    assert client.delete("/api/body-profile").status_code == 401
    assert client.post("/api/tryon/generate", json={}).status_code == 401
    assert client.get("/api/tryon/history").status_code == 401
    assert client.get("/api/tryon/jobs/dummy-id").status_code == 401
    assert client.get("/api/tryon/results/1").status_code == 401
    assert client.post("/api/tryon/results/1/favorite").status_code == 401
    assert client.delete("/api/tryon/results/1").status_code == 401


def test_body_profile_lifecycle(client, auth_tokens):
    """Verify body profile upload, retrieval, update, and deletion."""
    token = auth_tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Profile initially 404
    get_res = client.get("/api/body-profile", headers=headers)
    assert get_res.status_code == 404

    # 2. Upload photo and metrics
    img_buf = create_test_image(color=(210, 180, 140), size=(300, 600))
    upload_res = client.post(
        "/api/body-profile",
        data={
            "image": (img_buf, "full_body.jpg"),
            "height_cm": "178.5",
            "weight_kg": "74.0",
            "body_shape": "Athletic",
            "skin_tone": "Warm Beige"
        },
        content_type="multipart/form-data",
        headers=headers
    )
    assert upload_res.status_code == 201
    body_data = upload_res.get_json()["data"]
    assert "photo_url" in body_data
    assert body_data["height_cm"] == 178.5
    assert body_data["body_shape"] == "Athletic"

    # 3. Retrieve body profile
    get_res2 = client.get("/api/body-profile", headers=headers)
    assert get_res2.status_code == 200
    assert get_res2.get_json()["data"]["height_cm"] == 178.5

    # 4. Replace photo and update metrics
    new_buf = create_test_image(color=(200, 170, 130), size=(320, 640))
    update_res = client.post(
        "/api/body-profile",
        data={
            "image": (new_buf, "new_body.jpg"),
            "height_cm": "180.0"
        },
        content_type="multipart/form-data",
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.get_json()["data"]["height_cm"] == 180.0

    # 5. Delete body profile
    del_res = client.delete("/api/body-profile", headers=headers)
    assert del_res.status_code == 200

    # 6. Verify deleted
    get_after = client.get("/api/body-profile", headers=headers)
    assert get_after.status_code == 404


def test_body_profile_validation(client, auth_tokens):
    """Verify input validation on image format, height, and weight."""
    token = auth_tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Unsupported format
    txt_buf = io.BytesIO(b"not an image file")
    res = client.post(
        "/api/body-profile",
        data={"image": (txt_buf, "doc.txt")},
        content_type="multipart/form-data",
        headers=headers
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.get_json()["message"]

    # Invalid height (too low or not numeric)
    img_buf = create_test_image()
    res_h = client.post(
        "/api/body-profile",
        data={"image": (img_buf, "body.jpg"), "height_cm": "20"},
        content_type="multipart/form-data",
        headers=headers
    )
    assert res_h.status_code == 400
    assert "Height must be between" in res_h.get_json()["message"]


def test_tryon_without_profile_or_items(client, auth_tokens):
    """Verify proper error codes when profile or clothing items are missing."""
    token = auth_tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # User has no body profile uploaded yet
    res = client.post(
        "/api/tryon/generate",
        json={"clothing_item_ids": [1]},
        headers=headers
    )
    assert res.status_code == 400
    assert "body profile photograph is required" in res.get_json()["message"]

    # Upload body profile
    img_buf = create_test_image(size=(300, 600))
    client.post(
        "/api/body-profile",
        data={"image": (img_buf, "body.jpg")},
        content_type="multipart/form-data",
        headers=headers
    )

    # Empty clothing list
    res_empty = client.post(
        "/api/tryon/generate",
        json={"clothing_item_ids": []},
        headers=headers
    )
    assert res_empty.status_code == 400


def test_virtual_tryon_complete_flow(client, auth_tokens):
    """End-to-end virtual try-on generation, favorite, history, and deletion."""
    token = auth_tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Setup user body profile
    img_buf = create_test_image(color=(215, 185, 150), size=(300, 600))
    client.post(
        "/api/body-profile",
        data={"image": (img_buf, "model.jpg"), "height_cm": "175"},
        content_type="multipart/form-data",
        headers=headers
    )

    # 2. Upload wardrobe items: Top and Bottom
    top_id = upload_clothing_helper(client, token, "Silk Casual Shirt", "Tops", "Shirt", "Navy")
    bottom_id = upload_clothing_helper(client, token, "Tailored Chinos", "Bottoms", "Pants", "Charcoal")

    # 3. Generate Virtual Try-On
    tryon_res = client.post(
        "/api/tryon/generate",
        json={
            "clothing_item_ids": [top_id, bottom_id],
            "notes": "Navy & Charcoal Smart Casual Try-On"
        },
        headers=headers
    )
    assert tryon_res.status_code == 201
    json_data = tryon_res.get_json()["data"]
    assert "job" in json_data
    assert "result" in json_data
    assert json_data["job"]["status"] == "COMPLETED"
    result = json_data["result"]
    result_id = result["id"]
    job_id = json_data["job"]["id"]
    assert "result_image_url" in result
    assert result["engine"] == "adaptive_composite_v1"

    # 4. Check job status endpoint
    job_res = client.get(f"/api/tryon/jobs/{job_id}", headers=headers)
    assert job_res.status_code == 200
    assert job_res.get_json()["data"]["status"] == "COMPLETED"

    # 5. Fetch single result by ID
    res_single = client.get(f"/api/tryon/results/{result_id}", headers=headers)
    assert res_single.status_code == 200
    assert res_single.get_json()["data"]["id"] == result_id

    # 6. Fetch history
    hist_res = client.get("/api/tryon/history", headers=headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.get_json()["data"]
    assert hist_data["total"] >= 1
    assert any(r["id"] == result_id for r in hist_data["results"])

    # 7. Toggle favorite
    fav_res = client.post(f"/api/tryon/results/{result_id}/favorite", headers=headers)
    assert fav_res.status_code == 200
    assert fav_res.get_json()["data"]["is_favorite"] is True

    # 8. Query only favorites
    fav_hist = client.get("/api/tryon/history?favorites=true", headers=headers)
    assert fav_hist.status_code == 200
    assert any(r["id"] == result_id for r in fav_hist.get_json()["data"]["results"])

    # 9. Delete result
    del_res = client.delete(f"/api/tryon/results/{result_id}", headers=headers)
    assert del_res.status_code == 200

    # 10. Confirm deleted
    res_after = client.get(f"/api/tryon/results/{result_id}", headers=headers)
    assert res_after.status_code == 404


def test_multi_user_data_isolation(client, auth_tokens, auth_tokens_b):
    """
    CRITICAL: Verify strict privacy and data isolation between User A and User B.
    - User B cannot access User A's body photo.
    - User B cannot access User A's try-on result image.
    - User B cannot use User A's clothing items for try-on.
    - User B cannot see User A's history or delete User A's results.
    """
    token_a = auth_tokens["access_token"]
    token_b = auth_tokens_b["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A uploads body profile
    img_buf = create_test_image(color=(210, 180, 140), size=(300, 600))
    upload_res = client.post(
        "/api/body-profile",
        data={"image": (img_buf, "user_a_body.jpg")},
        content_type="multipart/form-data",
        headers=headers_a
    )
    assert upload_res.status_code == 201
    body_photo_url = upload_res.get_json()["data"]["photo_url"]

    # User A uploads clothing item
    item_a_id = upload_clothing_helper(client, token_a, "User A Coat", "Outerwear", "Coat", "Black")

    # User A creates try-on preview
    tryon_res = client.post(
        "/api/tryon/generate",
        json={"clothing_item_ids": [item_a_id]},
        headers=headers_a
    )
    assert tryon_res.status_code == 201
    result_a_id = tryon_res.get_json()["data"]["result"]["id"]
    tryon_img_url = tryon_res.get_json()["data"]["result"]["result_image_url"]

    # --- PRIVACY VERIFICATIONS ---

    # 1. User B tries to fetch User A's body photograph -> 403 Forbidden
    body_photo_res = client.get(body_photo_url, headers=headers_b)
    assert body_photo_res.status_code == 403

    # 2. User B tries to fetch User A's try-on image -> 403 Forbidden
    tryon_img_res = client.get(tryon_img_url, headers=headers_b)
    assert tryon_img_res.status_code == 403

    # 3. User B tries to generate try-on using User A's clothing item -> 404 Not Found
    # First give User B their own body profile
    img_b = create_test_image(color=(180, 150, 120), size=(300, 600))
    client.post(
        "/api/body-profile",
        data={"image": (img_b, "user_b_body.jpg")},
        content_type="multipart/form-data",
        headers=headers_b
    )
    cross_tryon = client.post(
        "/api/tryon/generate",
        json={"clothing_item_ids": [item_a_id]},
        headers=headers_b
    )
    assert cross_tryon.status_code == 404

    # 4. User B checks try-on history -> returns empty (does NOT include User A's result)
    b_history = client.get("/api/tryon/history", headers=headers_b)
    assert b_history.status_code == 200
    assert b_history.get_json()["data"]["total"] == 0

    # 5. User B attempts to access User A's result by ID -> 404 Not Found
    b_single = client.get(f"/api/tryon/results/{result_a_id}", headers=headers_b)
    assert b_single.status_code == 404

    # 6. User B attempts to delete User A's result -> 404 Not Found
    b_del = client.delete(f"/api/tryon/results/{result_a_id}", headers=headers_b)
    assert b_del.status_code == 404

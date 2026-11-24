import io
import pytest
from PIL import Image
from app.models.user import User
from app.models.profile import Profile
from app.models.clothing_item import ClothingItem
from app.models.recommendation import Recommendation, RecommendationItem
from app.models.body_profile import UserBodyProfile
from app.models.tryon import VirtualTryOnJob, VirtualTryOnResult
from app.extensions import db


def create_test_image(color=(20, 40, 80), size=(200, 200), format="JPEG"):
    """Generate in-memory test image with a specific solid color."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return file_obj


def test_auth_edge_cases(client):
    """Test boundary validation on auth endpoints."""
    # Invalid email format
    res = client.post("/api/auth/register", json={
        "username": "bademail_user",
        "email": "invalid-email-format",
        "password": "Password1234!"
    })
    assert res.status_code == 400, f"Expected 400 for bad email, got {res.status_code}"

    # Password too short (< 8 chars)
    res = client.post("/api/auth/register", json={
        "username": "shortpass_user",
        "email": "shortpass@example.com",
        "password": "123"
    })
    assert res.status_code == 400, f"Expected 400 for short password, got {res.status_code}"

    # Missing username
    res = client.post("/api/auth/register", json={
        "email": "missinguser@example.com",
        "password": "Password1234!"
    })
    assert res.status_code == 400

    # Non-existent login
    res = client.post("/api/auth/login", json={
        "email": "ghost@example.com",
        "password": "Password1234!"
    })
    assert res.status_code == 401

    # Malformed / empty JSON login
    res = client.post("/api/auth/login", data="not-json", content_type="text/plain")
    assert res.status_code in [400, 415]


def test_cross_user_clothing_tampering(client, auth_tokens, auth_tokens_b):
    """Verify User A cannot read, edit, or delete User B's clothing items."""
    user1_tok = auth_tokens["access_token"]
    user2_tok = auth_tokens_b["access_token"]

    # User 1 creates a clothing item
    img = create_test_image(color=(30, 60, 90))
    res1 = client.post(
        "/api/clothing",
        headers={"Authorization": f"Bearer {user1_tok}"},
        data={
            "name": "User 1 Exclusive Jacket",
            "category": "Outerwear",
            "subcategory": "Jackets",
            "image": (img, "item1.jpg", "image/jpeg")
        },
        content_type="multipart/form-data"
    )
    assert res1.status_code == 201
    item_id = res1.get_json()["data"]["id"]

    # User 2 tries to GET User 1's clothing item
    res_get = client.get(
        f"/api/clothing/{item_id}",
        headers={"Authorization": f"Bearer {user2_tok}"}
    )
    assert res_get.status_code in [403, 404], f"User 2 was able to access User 1's item! Got {res_get.status_code}"

    # User 2 tries to UPDATE User 1's clothing item
    res_put = client.put(
        f"/api/clothing/{item_id}",
        headers={"Authorization": f"Bearer {user2_tok}"},
        json={"name": "Hacked Jacket"}
    )
    assert res_put.status_code in [403, 404], f"User 2 was able to update User 1's item! Got {res_put.status_code}"

    # User 2 tries to DELETE User 1's clothing item
    res_del = client.delete(
        f"/api/clothing/{item_id}",
        headers={"Authorization": f"Bearer {user2_tok}"}
    )
    assert res_del.status_code in [403, 404], f"User 2 was able to delete User 1's item! Got {res_del.status_code}"


def test_path_traversal_on_images(client, auth_tokens):
    """Verify directory traversal is safely rejected on image serving endpoints."""
    user1_tok = auth_tokens["access_token"]
    traversal_paths = [
        "../../config.py",
        "..%2F..%2Fconfig.py",
        "....//....//config.py",
        "etc/passwd",
        "windows/win.ini"
    ]
    for path in traversal_paths:
        res = client.get(
            f"/api/clothing/images/{path}?token={user1_tok}",
            headers={"Authorization": f"Bearer {user1_tok}"}
        )
        assert res.status_code in [308, 400, 401, 403, 404], f"Path traversal vulnerable on {path}! Status: {res.status_code}"

        res_bp = client.get(
            f"/api/body-profile/images/{path}?token={user1_tok}",
            headers={"Authorization": f"Bearer {user1_tok}"}
        )
        assert res_bp.status_code in [308, 400, 401, 403, 404]

        res_to = client.get(
            f"/api/tryon/images/{path}?token={user1_tok}",
            headers={"Authorization": f"Bearer {user1_tok}"}
        )
        assert res_to.status_code in [308, 400, 401, 403, 404]


def test_cross_user_tryon_isolation(client, auth_tokens, auth_tokens_b):
    """Verify User 2 cannot access or inject User 1's items into try-on jobs."""
    user1_tok = auth_tokens["access_token"]
    user2_tok = auth_tokens_b["access_token"]

    # User 1 uploads body profile
    body_img = create_test_image(color=(220, 180, 150), size=(300, 600))
    client.post(
        "/api/body-profile",
        headers={"Authorization": f"Bearer {user1_tok}"},
        data={"image": (body_img, "body1.jpg", "image/jpeg"), "height_cm": 180.0, "weight_kg": 75.0},
        content_type="multipart/form-data"
    )

    # User 1 creates clothing items
    shirt_img = create_test_image(color=(20, 40, 80))
    res_shirt = client.post(
        "/api/clothing",
        headers={"Authorization": f"Bearer {user1_tok}"},
        data={
            "name": "User 1 Shirt",
            "category": "Tops",
            "subcategory": "Shirts",
            "image": (shirt_img, "s.jpg", "image/jpeg")
        },
        content_type="multipart/form-data"
    )
    assert res_shirt.status_code == 201
    user1_shirt_id = res_shirt.get_json()["data"]["id"]

    # User 2 uploads their own body profile
    body_img2 = create_test_image(color=(200, 160, 140), size=(300, 600))
    client.post(
        "/api/body-profile",
        headers={"Authorization": f"Bearer {user2_tok}"},
        data={"image": (body_img2, "body2.jpg", "image/jpeg"), "height_cm": 175.0, "weight_kg": 70.0},
        content_type="multipart/form-data"
    )

    # User 2 attempts to generate a try-on USING USER 1's CLOTHING ITEM
    res_tryon_hack = client.post(
        "/api/tryon/generate",
        headers={"Authorization": f"Bearer {user2_tok}"},
        json={"clothing_item_ids": [user1_shirt_id]}
    )
    assert res_tryon_hack.status_code in [400, 403, 404], (
        f"Security vulnerability: User 2 was able to use User 1's clothing item in try-on! Got {res_tryon_hack.status_code}"
    )


def test_recommendation_insufficient_items_handling(client, auth_tokens_b):
    """Verify recommendation engine handles accounts with insufficient wardrobe cleanly."""
    user2_tok = auth_tokens_b["access_token"]
    # User 2 has 0 clothes
    res = client.post(
        "/api/recommendations/generate",
        headers={"Authorization": f"Bearer {user2_tok}"},
        json={"occasion": "Casual"}
    )
    # Must NOT return 500 Internal Server Error
    assert res.status_code != 500, f"Recommendation returned 500 on empty wardrobe! Status: {res.status_code}"
    assert res.status_code in [200, 400], f"Expected 200 or 400, got {res.status_code}"


def test_database_cascade_deletes(app):
    """Verify that deleting a User cascades and cleans up all related records cleanly."""
    with app.app_context():
        # Create a test cascade user
        test_u = User(username="cascade_test_user", email="cascade@example.com")
        test_u.set_password("Password1234!")
        db.session.add(test_u)
        db.session.commit()
        uid = test_u.id

        # Add profile
        prof = Profile(user_id=uid, full_name="Cascade User", preferred_style="Casual")
        db.session.add(prof)

        # Add clothing item
        item = ClothingItem(
            user_id=uid,
            name="Cascade Shirt",
            category="Tops",
            subcategory="Shirts",
            image_url="/api/clothing/images/test.jpg"
        )
        db.session.add(item)

        # Add body profile
        bp = UserBodyProfile(user_id=uid, photo_url="/api/body-profile/images/test.jpg", height_cm=180.0)
        db.session.add(bp)
        db.session.commit()

        # Add try-on job and result
        job = VirtualTryOnJob(
            user_id=uid,
            body_profile_id=bp.id,
            body_photo_url="/api/body-profile/images/test.jpg",
            status="COMPLETED",
            engine_used="adaptive_composite_v1"
        )
        db.session.add(job)
        db.session.commit()

        res = VirtualTryOnResult(
            job_id=job.id,
            user_id=uid,
            result_image_url="/api/tryon/images/res.jpg",
            engine="adaptive_composite_v1"
        )
        db.session.add(res)
        db.session.commit()

        # Verify records exist
        assert Profile.query.filter_by(user_id=uid).count() == 1
        assert ClothingItem.query.filter_by(user_id=uid).count() == 1
        assert UserBodyProfile.query.filter_by(user_id=uid).count() == 1
        assert VirtualTryOnJob.query.filter_by(user_id=uid).count() == 1
        assert VirtualTryOnResult.query.filter_by(user_id=uid).count() == 1

        # Delete user
        db.session.delete(test_u)
        db.session.commit()

        # Verify CASCADE cleanup
        assert Profile.query.filter_by(user_id=uid).count() == 0, "Profile was not cascade deleted!"
        assert ClothingItem.query.filter_by(user_id=uid).count() == 0, "ClothingItem was not cascade deleted!"
        assert UserBodyProfile.query.filter_by(user_id=uid).count() == 0, "UserBodyProfile was not cascade deleted!"
        assert VirtualTryOnJob.query.filter_by(user_id=uid).count() == 0, "VirtualTryOnJob was not cascade deleted!"
        assert VirtualTryOnResult.query.filter_by(user_id=uid).count() == 0, "VirtualTryOnResult was not cascade deleted!"

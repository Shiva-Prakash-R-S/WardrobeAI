import pytest
from app.models.clothing_item import ClothingItem
from app.extensions import db
from app.services.color_compatibility import ColorCompatibilityService, CURATED_CLASSICS
from app.services.recommendation_service import OCCASIONS


def create_sample_clothing(user_id: int, name: str, category: str, subcategory: str, color: str, hex_val: str, occasion: str = None) -> ClothingItem:
    item = ClothingItem(
        user_id=user_id,
        name=name,
        category=category,
        subcategory=subcategory,
        primary_color=color,
        color_hex=hex_val,
        image_url=f"/static/uploads/{name.lower().replace(' ', '_')}.jpg",
        occasion=occasion,
        is_available=True
    )
    db.session.add(item)
    db.session.commit()
    return item


def test_get_occasions(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    res = client.get("/api/recommendations/occasions", headers=headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "occasions" in data
    assert len(data["occasions"]) == 10
    assert "College" in data["occasions"]
    assert "Office" in data["occasions"]
    assert "Formal" in data["occasions"]


def test_unauthenticated_recommendations(client):
    res1 = client.post("/api/recommendations/generate", json={"occasion": "Casual"})
    assert res1.status_code == 401

    res2 = client.get("/api/recommendations/history")
    assert res2.status_code == 401

    res3 = client.get("/api/recommendations/favorites")
    assert res3.status_code == 401


def test_empty_wardrobe_recommendations(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    res = client.post("/api/recommendations/generate", json={"occasion": "Casual"}, headers=headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_generate"] is False
    assert "empty" in data["message"].lower()
    assert len(data["recommendations"]) == 0


def test_insufficient_categories(client, auth_tokens, app):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    user_id = auth_tokens["user"]["id"]

    with app.app_context():
        create_sample_clothing(user_id, "Linen Shirt", "Tops", "Casual shirts", "White", "#FFFFFF")

    res = client.post("/api/recommendations/generate", json={"occasion": "Casual"}, headers=headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["can_generate"] is False
    assert "bottom" in data["message"].lower()
    assert len(data["recommendations"]) == 0


def test_color_compatibility_curated_pairs():
    required_pairs = [
        ("Navy", "Beige"),
        ("Black", "White"),
        ("Grey", "Black"),
        ("White", "Blue"),
        ("Olive", "Beige"),
        ("Brown", "Cream"),
        ("Maroon", "Black"),
        ("Blue", "Grey")
    ]
    for c1, c2 in required_pairs:
        eval_res = ColorCompatibilityService.evaluate_pair(c1, None, c2, None)
        assert eval_res["score"] >= 90
        assert eval_res["harmony_type"] == "curated_classic"
        assert len(eval_res["explanation"]) > 10


def test_color_compatibility_perceptual_cielab():
    # Test high contrast neutral + accent
    eval_res = ColorCompatibilityService.evaluate_pair("Black", "#000000", "Yellow", "#FFFF00")
    assert eval_res["score"] >= 80

    # Test monochromatic
    eval_mono = ColorCompatibilityService.evaluate_pair("Navy", "#000080", "Navy", "#102040")
    assert eval_mono["score"] >= 85
    assert eval_mono["harmony_type"] == "monochromatic"


def test_recommendation_generation_success(client, auth_tokens, app):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    user_id = auth_tokens["user"]["id"]

    with app.app_context():
        create_sample_clothing(user_id, "Navy Oxford Shirt", "Tops", "Formal shirts", "Navy", "#0F2043", "Formal")
        create_sample_clothing(user_id, "Beige Chinos", "Bottoms", "Chinos", "Beige", "#E1D5C0", "Office")
        create_sample_clothing(user_id, "White Minimal Sneakers", "Footwear", "Sneakers", "White", "#FFFFFF", "Casual")
        create_sample_clothing(user_id, "Brown Leather Watch", "Accessories", "Watches", "Brown", "#5D4037")

    res = client.post("/api/recommendations/generate", json={"occasion": "Office", "limit": 3}, headers=headers)
    assert res.status_code == 201
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["can_generate"] is True
    assert len(data["recommendations"]) >= 1

    first_rec = data["recommendations"][0]
    assert first_rec["occasion"] == "Office"
    assert first_rec["compatibility_score"] >= 75
    assert "scores" in first_rec
    assert first_rec["scores"]["color"] > 0
    assert first_rec["scores"]["occasion"] > 0
    assert first_rec["scores"]["style"] > 0
    assert first_rec["scores"]["completeness"] > 0
    assert first_rec["top"]["name"] == "Navy Oxford Shirt"
    assert first_rec["bottom"]["name"] == "Beige Chinos"
    assert first_rec["footwear"]["name"] == "White Minimal Sneakers"
    assert first_rec["accessory"]["name"] == "Brown Leather Watch"
    assert len(first_rec["explanation"]) > 20


def test_favorite_outfit_workflow(client, auth_tokens, app):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    user_id = auth_tokens["user"]["id"]

    with app.app_context():
        create_sample_clothing(user_id, "White T-Shirt", "Tops", "T-shirts", "White", "#FFFFFF")
        create_sample_clothing(user_id, "Blue Slim Jeans", "Bottoms", "Jeans", "Blue", "#1976D2")
        create_sample_clothing(user_id, "Classic Grey Sneakers", "Footwear", "Sneakers", "Grey", "#808084")

    # Generate outfit
    gen_res = client.post("/api/recommendations/generate", json={"occasion": "Casual"}, headers=headers)
    rec_id = gen_res.get_json()["data"]["recommendations"][0]["id"]

    # Initial favorites should be empty
    favs_empty = client.get("/api/recommendations/favorites", headers=headers)
    assert len(favs_empty.get_json()["data"]["items"]) == 0

    # Add to favorite
    add_fav = client.post(f"/api/recommendations/{rec_id}/favorite", headers=headers)
    assert add_fav.status_code == 200
    assert add_fav.get_json()["data"]["is_favorite"] is True

    # Check favorites list
    favs_after = client.get("/api/recommendations/favorites", headers=headers)
    assert len(favs_after.get_json()["data"]["items"]) == 1
    assert favs_after.get_json()["data"]["items"][0]["id"] == rec_id

    # Check details endpoint
    details = client.get(f"/api/recommendations/{rec_id}", headers=headers)
    assert details.status_code == 200
    assert details.get_json()["data"]["is_favorite"] is True

    # Remove from favorite
    rem_fav = client.delete(f"/api/recommendations/{rec_id}/favorite", headers=headers)
    assert rem_fav.status_code == 200
    assert rem_fav.get_json()["data"]["is_favorite"] is False

    # Check favorites list again
    favs_final = client.get("/api/recommendations/favorites", headers=headers)
    assert len(favs_final.get_json()["data"]["items"]) == 0


def test_recommendation_history_and_pagination(client, auth_tokens, app):
    headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    user_id = auth_tokens["user"]["id"]

    with app.app_context():
        create_sample_clothing(user_id, "Black Polo", "Tops", "Polo T-shirts", "Black", "#121214")
        create_sample_clothing(user_id, "Grey Trousers", "Bottoms", "Casual trousers", "Grey", "#808084")

    # Generate twice
    client.post("/api/recommendations/generate", json={"occasion": "College"}, headers=headers)
    client.post("/api/recommendations/generate", json={"occasion": "Office"}, headers=headers)

    # Get history
    history = client.get("/api/recommendations/history?page=1&per_page=10", headers=headers)
    assert history.status_code == 200
    data = history.get_json()["data"]
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Filter history by occasion
    filtered_hist = client.get("/api/recommendations/history?occasion=College", headers=headers)
    for it in filtered_hist.get_json()["data"]["items"]:
        assert it["occasion"] == "College"


def test_multi_user_isolation(client, auth_tokens, auth_tokens_b, app):
    headers_a = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
    headers_b = {"Authorization": f"Bearer {auth_tokens_b['access_token']}"}
    user_a_id = auth_tokens["user"]["id"]
    user_b_id = auth_tokens_b["user"]["id"]

    with app.app_context():
        # User A items
        create_sample_clothing(user_a_id, "User A Navy Shirt", "Tops", "Formal shirts", "Navy", "#0F2043")
        create_sample_clothing(user_a_id, "User A Khaki Pants", "Bottoms", "Chinos", "Beige", "#E1D5C0")

        # User B items
        create_sample_clothing(user_b_id, "User B Red Hoodie", "Tops", "Hoodies", "Red", "#D32F2F")
        create_sample_clothing(user_b_id, "User B Black Joggers", "Bottoms", "Joggers", "Black", "#121214")

    # User A generates
    res_a = client.post("/api/recommendations/generate", json={"occasion": "Office"}, headers=headers_a)
    rec_a_id = res_a.get_json()["data"]["recommendations"][0]["id"]
    top_a_name = res_a.get_json()["data"]["recommendations"][0]["top"]["name"]
    assert top_a_name == "User A Navy Shirt"

    # User B generates
    res_b = client.post("/api/recommendations/generate", json={"occasion": "Sports / Gym"}, headers=headers_b)
    rec_b_id = res_b.get_json()["data"]["recommendations"][0]["id"]
    top_b_name = res_b.get_json()["data"]["recommendations"][0]["top"]["name"]
    assert top_b_name == "User B Red Hoodie"

    # User B attempts to access User A's recommendation
    res_cross_get = client.get(f"/api/recommendations/{rec_a_id}", headers=headers_b)
    assert res_cross_get.status_code == 404

    # User B attempts to favorite User A's recommendation
    res_cross_fav = client.post(f"/api/recommendations/{rec_a_id}/favorite", headers=headers_b)
    assert res_cross_fav.status_code == 404

    # User A favorites their outfit
    client.post(f"/api/recommendations/{rec_a_id}/favorite", headers=headers_a)

    # User B's favorites should NOT contain User A's outfit
    favs_b = client.get("/api/recommendations/favorites", headers=headers_b)
    assert len(favs_b.get_json()["data"]["items"]) == 0

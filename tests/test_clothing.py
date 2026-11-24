import io
import pytest
from PIL import Image


def create_test_image(color=(15, 32, 67), size=(200, 200), format="JPEG"):
    """Generate in-memory test image with a specific solid color."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return file_obj


class TestClothingInventory:
    def test_successful_clothing_upload(self, client, auth_tokens):
        """1. Test successful clothing upload with multipart data and image."""
        img = create_test_image(color=(15, 32, 67))  # Navy blue
        data = {
            "name": "Navy Oxford Shirt",
            "category": "Tops",
            "subcategory": "Formal shirts",
            "brand": "Brooks Brothers",
            "size": "L",
            "pattern": "Plain",
            "season": "All-Season",
            "occasion": "Formal",
            "notes": "Premium cotton button-down shirt",
            "image": (img, "shirt.jpg", "image/jpeg")
        }
        res = client.post(
            "/api/clothing",
            data=data,
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 201
        payload = res.get_json()
        assert payload["success"] is True
        item = payload["data"]
        assert item["name"] == "Navy Oxford Shirt"
        assert item["category"] == "Tops"
        assert item["subcategory"] == "Formal shirts"
        assert item["primary_color"] == "Navy"
        assert item["image_url"].startswith("/api/clothing/images/clothing_")
        assert item["thumbnail_url"].startswith("/api/clothing/images/thumb_")

    def test_upload_without_authentication(self, client):
        """2. Test that unauthenticated upload requests are rejected with 401."""
        img = create_test_image()
        res = client.post(
            "/api/clothing",
            data={"name": "Shirt", "category": "Tops", "image": (img, "shirt.jpg")},
            content_type="multipart/form-data"
        )
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    def test_invalid_file_extension(self, client, auth_tokens):
        """3. Test that files with unsupported extensions are rejected."""
        fake_file = io.BytesIO(b"not an executable")
        res = client.post(
            "/api/clothing",
            data={
                "name": "Script Shirt",
                "category": "Tops",
                "image": (fake_file, "exploit.exe")
            },
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 400
        assert "Unsupported file extension" in res.get_json()["message"]

    def test_incorrect_actual_file_format(self, client, auth_tokens):
        """4. Test that non-image file with a fake image extension is rejected."""
        fake_img = io.BytesIO(b"This is just plain text content masquerading as an image")
        res = client.post(
            "/api/clothing",
            data={
                "name": "Fake Image Shirt",
                "category": "Tops",
                "image": (fake_img, "fake.jpg")
            },
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 400
        assert "Corrupted or invalid image" in res.get_json()["message"]

    def test_corrupted_image(self, client, auth_tokens):
        """5. Test that corrupted/truncated image byte stream is rejected."""
        corrupted = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01truncatedgarbage")
        res = client.post(
            "/api/clothing",
            data={
                "name": "Corrupted Shirt",
                "category": "Tops",
                "image": (corrupted, "corrupt.jpg")
            },
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 400
        assert "Corrupted or invalid image" in res.get_json()["message"]

    def test_oversized_image(self, client, auth_tokens):
        """6. Test that images exceeding the configured size limit are rejected."""
        # Create an in-memory buffer larger than 10MB
        oversized_data = b"0" * (11 * 1024 * 1024)
        oversized_file = io.BytesIO(oversized_data)
        res = client.post(
            "/api/clothing",
            data={
                "name": "Huge File",
                "category": "Tops",
                "image": (oversized_file, "huge.jpg")
            },
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code in (400, 413)

    def test_dominant_colour_detection(self, client, auth_tokens):
        """7. Test dominant color detection endpoint."""
        red_img = create_test_image(color=(211, 47, 47))  # Vivid Red
        res = client.post(
            "/api/clothing/detect-colors",
            data={"image": (red_img, "red.jpg", "image/jpeg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        data = payload["data"]
        assert data["primary_color"] == "Red"
        assert "color_hex" in data

    def test_list_clothing(self, client, auth_tokens):
        """8. Test listing user's clothing items with pagination metadata."""
        # Create 2 items
        for i in range(2):
            img = create_test_image(color=(50 * i, 100, 150))
            client.post(
                "/api/clothing",
                data={
                    "name": f"Item {i}",
                    "category": "Tops",
                    "subcategory": "T-shirts",
                    "image": (img, f"item{i}.jpg")
                },
                content_type="multipart/form-data",
                headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
            )

        res = client.get(
            "/api/clothing?page=1&per_page=10",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        assert len(payload["data"]["items"]) == 2
        assert payload["data"]["pagination"]["total"] == 2

    def test_category_filtering(self, client, auth_tokens):
        """9. Test filtering items by category (Tops vs Bottoms)."""
        img1 = create_test_image()
        client.post(
            "/api/clothing",
            data={"name": "Shirt", "category": "Tops", "subcategory": "Casual shirts", "image": (img1, "s.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )

        img2 = create_test_image()
        client.post(
            "/api/clothing",
            data={"name": "Jeans", "category": "Bottoms", "subcategory": "Jeans", "image": (img2, "j.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )

        # Filter by Tops
        res_tops = client.get(
            "/api/clothing?category=Tops",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res_tops.status_code == 200
        items_tops = res_tops.get_json()["data"]["items"]
        assert len(items_tops) == 1
        assert items_tops[0]["name"] == "Shirt"

        # Filter by Bottoms
        res_bottoms = client.get(
            "/api/clothing?category=Bottoms",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        items_bottoms = res_bottoms.get_json()["data"]["items"]
        assert len(items_bottoms) == 1
        assert items_bottoms[0]["name"] == "Jeans"

    def test_clothing_details_retrieval(self, client, auth_tokens):
        """10. Test retrieving full details of a specific clothing item."""
        img = create_test_image()
        create_res = client.post(
            "/api/clothing",
            data={"name": "Chinos", "category": "Bottoms", "subcategory": "Chinos", "image": (img, "c.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_id = create_res.get_json()["data"]["id"]

        res = client.get(
            f"/api/clothing/{item_id}",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["name"] == "Chinos"

    def test_clothing_metadata_update(self, client, auth_tokens):
        """11. Test updating clothing metadata fields."""
        img = create_test_image()
        create_res = client.post(
            "/api/clothing",
            data={"name": "Old Name", "category": "Tops", "subcategory": "T-shirts", "image": (img, "t.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_id = create_res.get_json()["data"]["id"]

        update_payload = {
            "name": "Updated Linen T-shirt",
            "brand": "Zara",
            "size": "M",
            "notes": "Updated note"
        }
        res = client.put(
            f"/api/clothing/{item_id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 200
        updated = res.get_json()["data"]
        assert updated["name"] == "Updated Linen T-shirt"
        assert updated["brand"] == "Zara"
        assert updated["size"] == "M"

    def test_image_replacement(self, client, auth_tokens):
        """12. Test replacing the photograph of an existing clothing item."""
        img1 = create_test_image(color=(10, 10, 10))
        create_res = client.post(
            "/api/clothing",
            data={"name": "Black Blazer", "category": "Tops", "subcategory": "Jackets", "image": (img1, "b1.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_id = create_res.get_json()["data"]["id"]
        old_img_url = create_res.get_json()["data"]["image_url"]

        img2 = create_test_image(color=(200, 200, 200))
        res = client.patch(
            f"/api/clothing/{item_id}/image",
            data={"image": (img2, "new_blazer.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 200
        new_img_url = res.get_json()["data"]["image_url"]
        assert new_img_url != old_img_url

    def test_clothing_deletion(self, client, auth_tokens):
        """13. Test deleting an item and verifying it is removed from the catalog."""
        img = create_test_image()
        create_res = client.post(
            "/api/clothing",
            data={"name": "To Delete", "category": "Footwear", "subcategory": "Sneakers", "image": (img, "del.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_id = create_res.get_json()["data"]["id"]

        del_res = client.delete(
            f"/api/clothing/{item_id}",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert del_res.status_code == 200

        # Verify subsequent retrieval returns 404
        get_res = client.get(
            f"/api/clothing/{item_id}",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert get_res.status_code == 404

    def test_user_a_cannot_access_user_b_item(self, client, auth_tokens, auth_tokens_b):
        """14. Test strict user isolation: User B cannot access User A's item."""
        img = create_test_image()
        create_res = client.post(
            "/api/clothing",
            data={"name": "User A Jacket", "category": "Tops", "subcategory": "Jackets", "image": (img, "ja.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_a_id = create_res.get_json()["data"]["id"]

        # User B attempts to access User A's item
        res = client.get(
            f"/api/clothing/{item_a_id}",
            headers={"Authorization": f"Bearer {auth_tokens_b['access_token']}"}
        )
        assert res.status_code == 403

    def test_user_a_cannot_update_user_b_item(self, client, auth_tokens, auth_tokens_b):
        """15. Test strict user isolation: User B cannot modify User A's item."""
        img = create_test_image()
        create_res = client.post(
            "/api/clothing",
            data={"name": "User A Watch", "category": "Accessories", "subcategory": "Watches", "image": (img, "w.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_a_id = create_res.get_json()["data"]["id"]

        res = client.put(
            f"/api/clothing/{item_a_id}",
            json={"name": "Hacked Name"},
            headers={"Authorization": f"Bearer {auth_tokens_b['access_token']}"}
        )
        assert res.status_code == 403

    def test_user_a_cannot_delete_user_b_item(self, client, auth_tokens, auth_tokens_b):
        """16. Test strict user isolation: User B cannot delete User A's item."""
        img = create_test_image()
        create_res = client.post(
            "/api/clothing",
            data={"name": "User A Belt", "category": "Accessories", "subcategory": "Belts", "image": (img, "b.jpg")},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        item_a_id = create_res.get_json()["data"]["id"]

        res = client.delete(
            f"/api/clothing/{item_a_id}",
            headers={"Authorization": f"Bearer {auth_tokens_b['access_token']}"}
        )
        assert res.status_code == 403

    def test_clothing_summary_accuracy(self, client, auth_tokens):
        """17. Test clothing summary endpoint returns accurate category and total counts."""
        items = [
            ("Formal Shirt", "Tops", "Formal shirts"),
            ("Chino Pants", "Bottoms", "Chinos"),
            ("White Sneakers", "Footwear", "Sneakers"),
            ("Leather Watch", "Accessories", "Watches"),
            ("Casual Polo", "Tops", "Polo T-shirts"),
        ]
        for name, cat, sub in items:
            img = create_test_image()
            client.post(
                "/api/clothing",
                data={"name": name, "category": cat, "subcategory": sub, "image": (img, "test.jpg")},
                content_type="multipart/form-data",
                headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
            )

        res = client.get(
            "/api/clothing/summary",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert res.status_code == 200
        summary = res.get_json()["data"]
        assert summary["total"] == 5
        assert summary["tops"] == 2
        assert summary["bottoms"] == 1
        assert summary["footwear"] == 1
        assert summary["accessories"] == 1
        assert summary["available"] == 5


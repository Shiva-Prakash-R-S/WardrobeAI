from typing import Dict, Any, Optional, Tuple
from sqlalchemy import or_, desc, asc
from app.extensions import db
from app.models.clothing_item import ClothingItem
from app.services.image_service import ImageStorageService, ImageValidationError
from app.services.color_service import ColorService

VALID_CATEGORIES = {
    "Tops": [
        "Formal shirts", "Casual shirts", "T-shirts", "Polo T-shirts",
        "Sweatshirts", "Hoodies", "Jackets", "Sweaters"
    ],
    "Bottoms": [
        "Jeans", "Formal trousers", "Casual trousers", "Chinos",
        "Shorts", "Joggers"
    ],
    "Footwear": [
        "Sneakers", "Formal shoes", "Casual shoes", "Sandals",
        "Boots", "Loafers"
    ],
    "Accessories": [
        "Watches", "Belts", "Sunglasses", "Caps",
        "Wallets", "Bracelets", "Other accessories"
    ]
}


class ClothingService:
    @staticmethod
    def create_clothing(user_id: int, form_data: dict, file) -> Tuple[Dict[str, Any], int]:
        """
        Create a new clothing item for the authenticated user.
        Handles image validation, color detection, and database persistence.
        """
        name = form_data.get("name", "").strip()
        category = form_data.get("category", "").strip()
        subcategory = form_data.get("subcategory", "").strip()

        if not name:
            return {"message": "Clothing item name is required."}, 400
        if not category:
            return {"message": "Category is required."}, 400
        if not subcategory:
            subcategory = "General"

        if not file:
            return {"message": "Clothing photograph is required."}, 400

        try:
            # First validate image and auto-detect colors if not provided
            img_obj = ImageStorageService.validate_and_open_image(file)
            detected = ColorService.detect_dominant_colors(img_obj)

            primary_color = form_data.get("primary_color") or detected["primary_color"]
            secondary_color = form_data.get("secondary_color") or detected["secondary_color"]
            color_hex = form_data.get("color_hex") or detected["color_hex"]

            # Save processed image and thumbnail to disk
            image_url, thumb_url, _, _ = ImageStorageService.save_clothing_image(file)

            # Persist clothing record
            new_item = ClothingItem(
                user_id=user_id,
                name=name,
                category=category,
                subcategory=subcategory,
                primary_color=primary_color,
                secondary_color=secondary_color,
                color_hex=color_hex,
                brand=form_data.get("brand") or None,
                size=form_data.get("size") or None,
                pattern=form_data.get("pattern") or None,
                season=form_data.get("season") or None,
                occasion=form_data.get("occasion") or None,
                image_url=image_url,
                thumbnail_url=thumb_url,
                notes=form_data.get("notes") or None,
                is_available=str(form_data.get("is_available", "true")).lower() in ("true", "1", "yes")
            )

            db.session.add(new_item)
            db.session.commit()

            return {
                "message": "Clothing item added successfully.",
                "clothing_item": new_item.to_dict()
            }, 201

        except ImageValidationError as e:
            return {"message": str(e)}, 400
        except Exception as e:
            db.session.rollback()
            return {"message": f"Failed to add clothing item: {str(e)}"}, 500

    @staticmethod
    def get_user_clothing(
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        color: Optional[str] = None,
        q: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        List clothing items strictly owned by user_id with filtering and pagination.
        """
        query = ClothingItem.query.filter_by(user_id=user_id)

        # Filters
        if category and category.lower() != "all":
            query = query.filter(ClothingItem.category.ilike(category))

        if subcategory and subcategory.lower() != "all":
            query = query.filter(ClothingItem.subcategory.ilike(subcategory))

        if color:
            query = query.filter(
                or_(
                    ClothingItem.primary_color.ilike(f"%{color}%"),
                    ClothingItem.secondary_color.ilike(f"%{color}%")
                )
            )

        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    ClothingItem.name.ilike(search_pattern),
                    ClothingItem.brand.ilike(search_pattern),
                    ClothingItem.subcategory.ilike(search_pattern),
                    ClothingItem.notes.ilike(search_pattern)
                )
            )

        # Sorting
        sort_column = getattr(ClothingItem, sort_by, ClothingItem.created_at)
        if order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        per_page = max(1, min(per_page, 100))
        page = max(1, page)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": [item.to_dict() for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }

    @staticmethod
    def get_clothing_by_id(item_id: int, user_id: int) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Fetch a specific clothing item by ID, enforcing user ownership.
        """
        item = db.session.get(ClothingItem, item_id)
        if not item:
            return {"message": "Clothing item not found."}, 404

        if item.user_id != user_id:
            return {"message": "Access denied. You do not own this clothing item."}, 403

        return {"clothing_item": item.to_dict()}, 200

    @staticmethod
    def update_clothing(item_id: int, user_id: int, update_data: dict) -> Tuple[Dict[str, Any], int]:
        """
        Update clothing item metadata, enforcing ownership.
        """
        item = db.session.get(ClothingItem, item_id)
        if not item:
            return {"message": "Clothing item not found."}, 404

        if item.user_id != user_id:
            return {"message": "Access denied. You do not own this clothing item."}, 403

        updatable_fields = [
            "name", "category", "subcategory", "primary_color",
            "secondary_color", "color_hex", "brand", "size",
            "pattern", "season", "occasion", "notes", "is_available"
        ]

        for field in updatable_fields:
            if field in update_data:
                val = update_data[field]
                if field == "is_available" and isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes")
                setattr(item, field, val)

        try:
            db.session.commit()
            return {
                "message": "Clothing item updated successfully.",
                "clothing_item": item.to_dict()
            }, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Failed to update clothing item: {str(e)}"}, 500

    @staticmethod
    def replace_clothing_image(item_id: int, user_id: int, file) -> Tuple[Dict[str, Any], int]:
        """
        Replace clothing image. Validates and writes new image before removing old files.
        """
        item = db.session.get(ClothingItem, item_id)
        if not item:
            return {"message": "Clothing item not found."}, 404

        if item.user_id != user_id:
            return {"message": "Access denied. You do not own this clothing item."}, 403

        if not file:
            return {"message": "Replacement image file is required."}, 400

        try:
            # Save new image first
            new_image_url, new_thumb_url, _, _ = ImageStorageService.save_clothing_image(file)

            old_image_url = item.image_url
            old_thumb_url = item.thumbnail_url

            # Update database
            item.image_url = new_image_url
            item.thumbnail_url = new_thumb_url
            db.session.commit()

            # Clean up old images safely on disk
            ImageStorageService.delete_clothing_images(old_image_url, old_thumb_url)

            return {
                "message": "Clothing image replaced successfully.",
                "clothing_item": item.to_dict()
            }, 200

        except ImageValidationError as e:
            return {"message": str(e)}, 400
        except Exception as e:
            db.session.rollback()
            return {"message": f"Failed to replace clothing image: {str(e)}"}, 500

    @staticmethod
    def delete_clothing(item_id: int, user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Delete clothing item from database and delete stored files safely.
        """
        item = db.session.get(ClothingItem, item_id)
        if not item:
            return {"message": "Clothing item not found."}, 404

        if item.user_id != user_id:
            return {"message": "Access denied. You do not own this clothing item."}, 403

        image_url = item.image_url
        thumbnail_url = item.thumbnail_url

        try:
            db.session.delete(item)
            db.session.commit()

            # Safely delete disk files after DB commit succeeds
            ImageStorageService.delete_clothing_images(image_url, thumbnail_url)

            return {"message": "Clothing item deleted successfully."}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"Failed to delete clothing item: {str(e)}"}, 500

    @staticmethod
    def get_clothing_summary(user_id: int) -> Dict[str, Any]:
        """
        Calculate total and category counts strictly for the authenticated user.
        """
        total = ClothingItem.query.filter_by(user_id=user_id).count()
        tops = ClothingItem.query.filter_by(user_id=user_id).filter(ClothingItem.category.ilike("Tops")).count()
        bottoms = ClothingItem.query.filter_by(user_id=user_id).filter(ClothingItem.category.ilike("Bottoms")).count()
        footwear = ClothingItem.query.filter_by(user_id=user_id).filter(ClothingItem.category.ilike("Footwear")).count()
        accessories = ClothingItem.query.filter_by(user_id=user_id).filter(ClothingItem.category.ilike("Accessories")).count()
        available = ClothingItem.query.filter_by(user_id=user_id, is_available=True).count()

        return {
            "total": total,
            "tops": tops,
            "bottoms": bottoms,
            "footwear": footwear,
            "accessories": accessories,
            "available": available
        }


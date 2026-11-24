import logging
from typing import Tuple, Dict, Any, Optional
from werkzeug.datastructures import FileStorage
from app.extensions import db
from app.models.body_profile import UserBodyProfile
from app.services.image_service import ImageStorageService, ImageValidationError

logger = logging.getLogger(__name__)


class BodyProfileService:
    @staticmethod
    def get_body_profile(user_id: int) -> Optional[UserBodyProfile]:
        """Fetch the active body profile for the given user."""
        return UserBodyProfile.query.filter_by(user_id=user_id, is_active=True).first()

    @staticmethod
    def create_or_update_body_profile(
        user_id: int,
        form_data: Dict[str, Any],
        file: Optional[FileStorage]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Creates a new body profile or updates an existing one for the authenticated user.
        Replaces existing photograph safely on disk.
        """
        existing_profile = UserBodyProfile.query.filter_by(user_id=user_id).first()

        # Check if an image is provided or if updating attributes on existing profile
        if not file and not existing_profile:
            return {"message": "A full-body photograph is required to create your body profile."}, 400

        image_url = None
        thumb_url = None
        old_image_url = None
        old_thumb_url = None

        if file:
            try:
                image_url, thumb_url, _, _ = ImageStorageService.save_body_image(file)
            except ImageValidationError as e:
                return {"message": str(e)}, 400
            except Exception as e:
                logger.error(f"Failed to process body image for user {user_id}: {e}", exc_info=True)
                return {"message": "An error occurred while processing the body photograph."}, 500

            if existing_profile:
                old_image_url = existing_profile.photo_url
                old_thumb_url = existing_profile.thumbnail_url

        try:
            # Parse optional numeric and descriptive fields
            height_cm = None
            if form_data.get("height_cm"):
                try:
                    height_cm = float(form_data["height_cm"])
                    if not (50.0 <= height_cm <= 260.0):
                        return {"message": "Height must be between 50 and 260 cm."}, 400
                except (ValueError, TypeError):
                    return {"message": "Invalid height value."}, 400

            weight_kg = None
            if form_data.get("weight_kg"):
                try:
                    weight_kg = float(form_data["weight_kg"])
                    if not (20.0 <= weight_kg <= 300.0):
                        return {"message": "Weight must be between 20 and 300 kg."}, 400
                except (ValueError, TypeError):
                    return {"message": "Invalid weight value."}, 400

            body_shape = form_data.get("body_shape", "").strip() or None
            skin_tone = form_data.get("skin_tone", "").strip() or None
            gender = form_data.get("gender", "").strip() or None

            if existing_profile:
                if image_url:
                    existing_profile.photo_url = image_url
                    existing_profile.thumbnail_url = thumb_url
                if "height_cm" in form_data:
                    existing_profile.height_cm = height_cm
                if "weight_kg" in form_data:
                    existing_profile.weight_kg = weight_kg
                if "body_shape" in form_data:
                    existing_profile.body_shape = body_shape
                if "skin_tone" in form_data:
                    existing_profile.skin_tone = skin_tone
                if "gender" in form_data:
                    existing_profile.gender = gender

                existing_profile.is_active = True
                db.session.commit()

                # Clean up previous images after successful commit
                if old_image_url and image_url:
                    ImageStorageService.delete_body_images(old_image_url, old_thumb_url)

                return {
                    "message": "Body profile updated successfully.",
                    "body_profile": existing_profile.to_dict()
                }, 200
            else:
                profile = UserBodyProfile(
                    user_id=user_id,
                    photo_url=image_url,
                    thumbnail_url=thumb_url,
                    height_cm=height_cm,
                    weight_kg=weight_kg,
                    body_shape=body_shape,
                    skin_tone=skin_tone,
                    gender=gender,
                    is_active=True
                )
                db.session.add(profile)
                db.session.commit()

                return {
                    "message": "Body profile created successfully.",
                    "body_profile": profile.to_dict()
                }, 201

        except Exception as e:
            db.session.rollback()
            # If new files were written but DB transaction failed, delete new files
            if image_url:
                ImageStorageService.delete_body_images(image_url, thumb_url)
            logger.error(f"Database error saving body profile for user {user_id}: {e}", exc_info=True)
            return {"message": "Failed to save body profile to database."}, 500

    @staticmethod
    def delete_body_profile(user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Deletes the authenticated user's body profile and stored photograph files.
        """
        profile = UserBodyProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"message": "Body profile not found."}, 404

        photo_url = profile.photo_url
        thumb_url = profile.thumbnail_url

        try:
            db.session.delete(profile)
            db.session.commit()
            ImageStorageService.delete_body_images(photo_url, thumb_url)
            return {"message": "Body profile deleted successfully."}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting body profile for user {user_id}: {e}", exc_info=True)
            return {"message": "Failed to delete body profile."}, 500

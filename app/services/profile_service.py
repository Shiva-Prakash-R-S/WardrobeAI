from app.extensions import db
from app.models.profile import Profile
from app.models.user import User

class ProfileService:

    @staticmethod
    def get_profile_by_user_id(user_id: int) -> tuple[dict | None, str | None]:
        user = db.session.get(User, user_id)
        if not user:
            return None, "User not found"

        profile = Profile.query.filter_by(user_id=user_id).first()
        if not profile:
            # Fallback auto-creation if not present
            profile = Profile(user_id=user_id, full_name=user.username)
            db.session.add(profile)
            db.session.commit()

        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": profile.full_name,
            "profile_photo": profile.profile_photo,
            "preferred_style": profile.preferred_style,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
        }, None

    @staticmethod
    def update_profile(user_id: int, data: dict) -> tuple[dict | None, str | None]:
        profile = Profile.query.filter_by(user_id=user_id).first()
        if not profile:
            return None, "Profile not found"

        full_name = data.get("full_name")
        if full_name is not None:
            full_name = full_name.strip()
            if not full_name:
                return None, "Full name cannot be empty"
            profile.full_name = full_name

        if "preferred_style" in data:
            profile.preferred_style = data["preferred_style"]

        if "profile_photo" in data:
            profile.profile_photo = data["profile_photo"]

        try:
            db.session.commit()
            return profile.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, f"Database error updating profile: {str(e)}"

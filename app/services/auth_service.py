from datetime import datetime, timezone
from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db
from app.models.user import User
from app.models.profile import Profile
from app.models.token_blocklist import TokenBlocklist

class AuthService:

    @staticmethod
    def register_user(username: str, email: str, password: str, full_name: str) -> tuple[dict | None, str | None]:
        # Check duplicate email
        if User.query.filter_by(email=email.lower()).first():
            return None, "Email address already registered"

        # Check duplicate username
        if User.query.filter_by(username=username).first():
            return None, "Username already taken"

        # Create user and profile atomically
        try:
            user = User(
                username=username,
                email=email.lower(),
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # Populates user.id

            profile = Profile(
                user_id=user.id,
                full_name=full_name,
                preferred_style="Classic Elegance"
            )
            db.session.add(profile)
            db.session.commit()

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": profile.full_name,
                "created_at": user.created_at.isoformat()
            }, None
        except Exception as e:
            db.session.rollback()
            return None, f"Database error during registration: {str(e)}"

    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple[dict | None, str | None]:
        user = User.query.filter_by(email=email.lower()).first()
        if not user or not user.check_password(password):
            return None, "Invalid email or password"

        if not user.is_active:
            return None, "Account is disabled. Please contact support."

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.profile.full_name if user.profile else user.username,
            "profile_photo": user.profile.profile_photo if user.profile else None,
            "preferred_style": user.profile.preferred_style if user.profile else None
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user_data
        }, None

    @staticmethod
    def revoke_token(jti: str, token_type: str, user_id: int, exp_timestamp: int) -> bool:
        """Revoke a token server-side by saving its unique jti in TokenBlocklist."""
        try:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            revoked_token = TokenBlocklist(
                jti=jti,
                token_type=token_type,
                user_id=user_id,
                expires_at=expires_at
            )
            db.session.add(revoked_token)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def is_token_revoked(jwt_payload: dict) -> bool:
        """Callback for flask_jwt_extended to verify whether a token has been revoked."""
        jti = jwt_payload.get("jti")
        token = TokenBlocklist.query.filter_by(jti=jti).first()
        return token is not None


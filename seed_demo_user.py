import os
import sys

# Ensure backend root is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.profile import Profile

DEMO_EMAIL = "demo@wardrobeai.local"
DEMO_USERNAME = "demo_user"
DEMO_PASSWORD = "WardrobeAI@Demo2026!"
DEMO_FULL_NAME = "Demo User"
DEMO_PREFERRED_STYLE = "Modern Minimalist"


def seed_demo_account():
    app = create_app("default")
    with app.app_context():
        # Check if demo account already exists by email or username
        user = User.query.filter(
            (User.email == DEMO_EMAIL) | (User.username == DEMO_USERNAME)
        ).first()

        if user:
            print(f"Demo account already exists (ID: {user.id}, email: {user.email}).")
            # Ensure credentials, active status, and profile are synchronized
            user.email = DEMO_EMAIL
            user.username = DEMO_USERNAME
            user.is_active = True
            user.set_password(DEMO_PASSWORD)

            if not user.profile:
                profile = Profile(
                    user_id=user.id,
                    full_name=DEMO_FULL_NAME,
                    preferred_style=DEMO_PREFERRED_STYLE
                )
                db.session.add(profile)
            else:
                user.profile.full_name = DEMO_FULL_NAME
                user.profile.preferred_style = DEMO_PREFERRED_STYLE

            db.session.commit()
            print("Demo account credentials, active status, and profile updated successfully.")
            return user.to_dict()

        # Create new demo account
        new_user = User(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            is_active=True
        )
        new_user.set_password(DEMO_PASSWORD)
        db.session.add(new_user)
        db.session.flush()  # Populate new_user.id for profile foreign key

        new_profile = Profile(
            user_id=new_user.id,
            full_name=DEMO_FULL_NAME,
            preferred_style=DEMO_PREFERRED_STYLE
        )
        db.session.add(new_profile)
        db.session.commit()

        print(f"Successfully created demo account (ID: {new_user.id}, email: {DEMO_EMAIL}).")
        return new_user.to_dict()


if __name__ == "__main__":
    seed_demo_account()


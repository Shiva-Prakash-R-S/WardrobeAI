from datetime import datetime, timezone
from app.extensions import db

class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    full_name = db.Column(db.String(100), nullable=False)
    profile_photo = db.Column(db.String(255), nullable=True)
    preferred_style = db.Column(db.String(100), nullable=True, default="Classic Elegance")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    user = db.relationship("User", back_populates="profile")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "profile_photo": self.profile_photo,
            "preferred_style": self.preferred_style,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Profile {self.full_name} for user_id={self.user_id}>"


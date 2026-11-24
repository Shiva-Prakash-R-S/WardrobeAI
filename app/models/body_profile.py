from datetime import datetime, timezone
from app.extensions import db


class UserBodyProfile(db.Model):
    __tablename__ = "user_body_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    photo_url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    body_shape = db.Column(db.String(50), nullable=True)
    skin_tone = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(30), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = db.relationship("User", backref=db.backref("body_profile", uselist=False, cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "photo_url": self.photo_url,
            "thumbnail_url": self.thumbnail_url,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "body_shape": self.body_shape,
            "skin_tone": self.skin_tone,
            "gender": self.gender,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<UserBodyProfile id={self.id} user_id={self.user_id}>"

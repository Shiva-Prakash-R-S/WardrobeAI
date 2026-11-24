from datetime import datetime, timezone
from app.extensions import db


class ClothingItem(db.Model):
    __tablename__ = "clothing_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    subcategory = db.Column(db.String(50), nullable=False, index=True)
    primary_color = db.Column(db.String(50), nullable=True)
    secondary_color = db.Column(db.String(50), nullable=True)
    color_hex = db.Column(db.String(10), nullable=True)
    brand = db.Column(db.String(100), nullable=True)
    size = db.Column(db.String(20), nullable=True)
    pattern = db.Column(db.String(50), nullable=True)
    season = db.Column(db.String(50), nullable=True)
    occasion = db.Column(db.String(50), nullable=True)
    image_url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

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

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "color_hex": self.color_hex,
            "brand": self.brand,
            "size": self.size,
            "pattern": self.pattern,
            "season": self.season,
            "occasion": self.occasion,
            "image_url": self.image_url,
            "thumbnail_url": self.thumbnail_url,
            "notes": self.notes,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ClothingItem {self.id}: {self.name} ({self.category}/{self.subcategory})>"


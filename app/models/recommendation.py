from datetime import datetime, timezone
from app.extensions import db


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    occasion = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    compatibility_score = db.Column(db.Integer, nullable=False)
    color_score = db.Column(db.Integer, nullable=False)
    occasion_score = db.Column(db.Integer, nullable=False)
    completeness_score = db.Column(db.Integer, nullable=False)
    style_score = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    items = db.relationship(
        "RecommendationItem",
        back_populates="recommendation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def to_dict(self):
        item_dicts = [item.to_dict() for item in self.items]
        role_map = {}
        for it in item_dicts:
            role = it.get("role")
            if role and role not in role_map:
                role_map[role] = it.get("clothing_item")

        return {
            "id": self.id,
            "user_id": self.user_id,
            "occasion": self.occasion,
            "title": self.title,
            "compatibility_score": self.compatibility_score,
            "scores": {
                "overall": self.compatibility_score,
                "color": self.color_score,
                "occasion": self.occasion_score,
                "completeness": self.completeness_score,
                "style": self.style_score
            },
            "explanation": self.explanation,
            "is_favorite": self.is_favorite,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": item_dicts,
            "top": role_map.get("top"),
            "bottom": role_map.get("bottom"),
            "footwear": role_map.get("footwear"),
            "accessory": role_map.get("accessory")
        }

    def __repr__(self):
        return f"<Recommendation {self.id}: {self.title} ({self.occasion} - {self.compatibility_score}%)>"


class RecommendationItem(db.Model):
    __tablename__ = "recommendation_items"

    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    clothing_item_id = db.Column(
        db.Integer,
        db.ForeignKey("clothing_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = db.Column(db.String(30), nullable=False)  # 'top', 'bottom', 'footwear', 'accessory'

    recommendation = db.relationship("Recommendation", back_populates="items")
    clothing_item = db.relationship("ClothingItem", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "clothing_item_id": self.clothing_item_id,
            "clothing_item": self.clothing_item.to_dict() if self.clothing_item else None
        }

    def __repr__(self):
        return f"<RecommendationItem {self.id}: Rec {self.recommendation_id} Item {self.clothing_item_id} ({self.role})>"

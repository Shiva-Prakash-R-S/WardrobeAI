import uuid
from datetime import datetime, timezone
from app.extensions import db


class VirtualTryOnJob(db.Model):
    __tablename__ = "virtual_tryon_jobs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    body_profile_id = db.Column(
        db.Integer,
        db.ForeignKey("user_body_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    body_photo_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="PENDING", nullable=False, index=True)
    progress_percent = db.Column(db.Integer, default=0, nullable=False)
    stage_message = db.Column(db.String(255), default="Initiating virtual try-on...")
    error_message = db.Column(db.Text, nullable=True)
    engine_used = db.Column(db.String(50), default="adaptive_composite_v1", nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", backref=db.backref("tryon_jobs", cascade="all, delete-orphan", lazy="dynamic"))
    items = db.relationship("TryOnJobItem", backref="job", cascade="all, delete-orphan", lazy="joined")
    result = db.relationship("VirtualTryOnResult", backref="job", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "body_profile_id": self.body_profile_id,
            "body_photo_url": self.body_photo_url,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "stage_message": self.stage_message,
            "error_message": self.error_message,
            "engine_used": self.engine_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "items": [item.to_dict() for item in self.items] if self.items else [],
            "result": self.result.to_dict() if self.result else None,
        }

    def __repr__(self):
        return f"<VirtualTryOnJob id={self.id} user_id={self.user_id} status={self.status}>"


class TryOnJobItem(db.Model):
    __tablename__ = "tryon_job_items"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.String(36),
        db.ForeignKey("virtual_tryon_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    clothing_item_id = db.Column(
        db.Integer,
        db.ForeignKey("clothing_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    slot = db.Column(db.String(50), nullable=False)  # 'top', 'bottom', 'shoes', 'outerwear', 'dress', 'accessory'

    clothing_item = db.relationship("ClothingItem")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "clothing_item_id": self.clothing_item_id,
            "slot": self.slot,
            "clothing_item": self.clothing_item.to_dict() if self.clothing_item else None
        }


class VirtualTryOnResult(db.Model):
    __tablename__ = "virtual_tryon_results"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.String(36),
        db.ForeignKey("virtual_tryon_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    result_image_url = db.Column(db.String(255), nullable=False)
    engine = db.Column(db.String(50), default="adaptive_composite_v1", nullable=False)
    engine_version = db.Column(db.String(50), default="1.0.0", nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user = db.relationship("User", backref=db.backref("tryon_results", cascade="all, delete-orphan", lazy="dynamic"))

    def to_dict(self, include_job_items=True):
        data = {
            "id": self.id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "result_image_url": self.result_image_url,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "is_favorite": self.is_favorite,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_job_items and self.job:
            data["body_photo_url"] = self.job.body_photo_url
            data["items"] = [item.to_dict() for item in self.job.items] if self.job.items else []
        return data

    def __repr__(self):
        return f"<VirtualTryOnResult id={self.id} job_id={self.job_id} user_id={self.user_id}>"


class SavedTryOnPreview(db.Model):
    __tablename__ = "saved_tryon_previews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    result_id = db.Column(
        db.Integer,
        db.ForeignKey("virtual_tryon_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = db.Column(db.String(150), nullable=False, default="My Styled Outfit")
    notes = db.Column(db.Text, nullable=True)
    saved_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user = db.relationship("User", backref=db.backref("saved_previews", cascade="all, delete-orphan", lazy="dynamic"))
    result = db.relationship("VirtualTryOnResult", backref=db.backref("saved_entries", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "result_id": self.result_id,
            "title": self.title,
            "notes": self.notes,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
            "result": self.result.to_dict() if self.result else None
        }

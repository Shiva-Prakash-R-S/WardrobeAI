from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    profile = db.relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    revoked_tokens = db.relationship(
        "TokenBlocklist",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    clothing_items = db.relationship(
        "ClothingItem",
        backref="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        """Hash and set the user password using Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the plain text password against the hashed password."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Return safe dictionary representation without password_hash."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "profile": self.profile.to_dict() if self.profile else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"


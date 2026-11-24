from datetime import datetime, timezone
from app.extensions import db

class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    revoked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", back_populates="revoked_tokens")

    def __repr__(self):
        return f"<TokenBlocklist jti={self.jti} type={self.token_type} user_id={self.user_id}>"


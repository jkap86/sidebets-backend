from __future__ import annotations
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from extensions import db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bet_participant import BetParticipant


class User(db.Model):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    bet_participations: Mapped[list["BetParticipant"]] = relationship(
        "BetParticipant", back_populates="user", cascade="all, delete-orphan"
    )

    @classmethod
    def create(cls, username: str, password: str) -> "User":
        return cls(
            username=username.lower().strip(),  # type: ignore
            password_hash=generate_password_hash(password, method="pbkdf2:sha256", salt_length=16),  # type: ignore
        )

    def verify_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User user_id={self.user_id} username={self.username}>"

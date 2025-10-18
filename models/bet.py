from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from extensions import db
from typing import TYPE_CHECKING
import enum

if TYPE_CHECKING:
    from .bet_participant import BetParticipant
    from .user import User


class BetStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class BetType(enum.Enum):
    TEAM = "team"
    PLAYER = "player"
    CUSTOM = "custom"


class Bet(db.Model):
    __tablename__ = "bets"

    bet_id: Mapped[int] = mapped_column(primary_key=True)

    # Bet details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bet_type: Mapped[BetType] = mapped_column(SQLEnum(BetType), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Bet positions defined upfront
    position_a: Mapped[str] = mapped_column(String(255), nullable=False)
    position_b: Mapped[str] = mapped_column(String(255), nullable=False)

    # Who created the bet
    created_by: Mapped[int] = mapped_column(
        db.ForeignKey("users.user_id"), nullable=False
    )

    # Status and timestamps
    status: Mapped[BetStatus] = mapped_column(
        SQLEnum(BetStatus), default=BetStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    event_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Outcome (only set when status = SETTLED)
    winner_id: Mapped[int | None] = mapped_column(
        db.ForeignKey("users.user_id"), nullable=True
    )
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    participants: Mapped[list["BetParticipant"]] = relationship(
        "BetParticipant", back_populates="bet", cascade="all, delete-orphan"
    )
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    winner: Mapped["User | None"] = relationship("User", foreign_keys=[winner_id])

    def __repr__(self) -> str:
        return (
            f"<Bet bet_id={self.bet_id} title={self.title} status={self.status.value}>"
        )

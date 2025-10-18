from __future__ import annotations
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from extensions import db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bet import Bet
    from .user import User


class BetParticipant(db.Model):
    __tablename__ = "bet_participants"
    __table_args__ = (UniqueConstraint("bet_id", "user_id", name="uq_bet_user"),)

    participant_id: Mapped[int] = mapped_column(primary_key=True)
    bet_id: Mapped[int] = mapped_column(db.ForeignKey("bets.bet_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.user_id"), nullable=False)

    # Role in the bet
    side: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'proposer' or 'acceptor'

    # Relationships
    bet: Mapped["Bet"] = relationship("Bet", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="bet_participations")

    def __repr__(self) -> str:
        return f"<BetParticipant bet_id={self.bet_id} user_id={self.user_id} side={self.side}>"

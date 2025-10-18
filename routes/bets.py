from __future__ import annotations
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from extensions import db
from models import Bet, BetParticipant, BetStatus, BetType

bets_bp = Blueprint("bets", __name__)


# --------------- Helper Functions ---------------
def serialize_bet(bet: Bet, current_user_id: int | None = None) -> dict:
    """Serialize a bet to JSON with participant info"""
    participants_data = []
    proposer = None
    acceptor = None

    for p in bet.participants:
        participant_info = {
            "user_id": p.user_id,
            "username": p.user.username,
            "side": p.side,
        }
        participants_data.append(participant_info)

        if p.side == "proposer":
            proposer = participant_info
        elif p.side == "acceptor":
            acceptor = participant_info

    # Determine if current user is involved
    user_side = None
    if current_user_id:
        for p in bet.participants:
            if p.user_id == current_user_id:
                user_side = p.side
                break

    return {
        "bet_id": bet.bet_id,
        "title": bet.title,
        "description": bet.description,
        "bet_type": bet.bet_type.value,
        "amount": float(bet.amount),
        "status": bet.status.value,
        "created_by": bet.created_by,
        "creator_username": bet.creator.username,
        "position_a": bet.position_a,
        "position_b": bet.position_b,
        "created_at": bet.created_at.isoformat() if bet.created_at else None,
        "accepted_at": bet.accepted_at.isoformat() if bet.accepted_at else None,
        "settled_at": bet.settled_at.isoformat() if bet.settled_at else None,
        "event_date": bet.event_date.isoformat() if bet.event_date else None,
        "winner_id": bet.winner_id,
        "winner_username": bet.winner.username if bet.winner else None,
        "outcome_notes": bet.outcome_notes,
        "proposer": proposer,
        "acceptor": acceptor,
        "participants": participants_data,
        "user_side": user_side,
    }


# --------------- Routes ---------------


@bets_bp.post("/")
@jwt_required()
def create_bet():
    """Create a new bet proposition"""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Validate required fields
    title = (data.get("title") or "").strip()
    amount = data.get("amount")
    bet_type = data.get("bet_type", "custom")
    position_a = (data.get("position_a") or "").strip()
    position_b = (data.get("position_b") or "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    if not amount or float(amount) <= 0:
        return jsonify({"error": "Amount must be greater than 0"}), 400

    if not position_a or not position_b:
        return jsonify({"error": "Both position_a and position_b are required"}), 400

    # Validate bet_type
    try:
        bet_type_enum = BetType(bet_type)
    except ValueError:
        return (
            jsonify(
                {
                    "error": f"Invalid bet_type. Must be one of: {[t.value for t in BetType]}"
                }
            ),
            400,
        )

    # Optional fields
    description = data.get("description")
    event_date_str = data.get("event_date")

    # Parse event_date if provided
    event_date = None
    if event_date_str:
        try:
            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid event_date format. Use ISO 8601"}), 400

    # Create bet
    bet = Bet()
    bet.title = title
    bet.description = description
    bet.bet_type = bet_type_enum
    bet.amount = float(amount)
    bet.created_by = user_id
    bet.status = BetStatus.PENDING
    bet.event_date = event_date
    bet.position_a = position_a
    bet.position_b = position_b

    db.session.add(bet)
    db.session.flush()  # Get bet_id

    # Add proposer as participant (proposer always gets position_a)
    proposer = BetParticipant()
    proposer.bet_id = bet.bet_id
    proposer.user_id = user_id
    proposer.side = "proposer"

    db.session.add(proposer)

    try:
        db.session.commit()
        return jsonify(serialize_bet(bet, user_id)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bets_bp.get("/")
@jwt_required(optional=True)
def list_bets():
    """List bets with optional filters"""
    current_user_id = None
    identity = get_jwt_identity()
    if identity:
        current_user_id = int(identity)

    # Query params for filtering
    status = request.args.get("status")  # pending, active, settled, cancelled
    bet_type = request.args.get("bet_type")  # team, player, custom
    user_id = request.args.get("user_id")  # filter by participant

    query = Bet.query

    # Filter by status
    if status:
        try:
            status_enum = BetStatus(status)
            query = query.filter(Bet.status == status_enum)
        except ValueError:
            return (
                jsonify(
                    {
                        "error": f"Invalid status. Must be one of: {[s.value for s in BetStatus]}"
                    }
                ),
                400,
            )

    # Filter by bet_type
    if bet_type:
        try:
            type_enum = BetType(bet_type)
            query = query.filter(Bet.bet_type == type_enum)
        except ValueError:
            return (
                jsonify(
                    {
                        "error": f"Invalid bet_type. Must be one of: {[t.value for t in BetType]}"
                    }
                ),
                400,
            )

    # Filter by user participation
    if user_id:
        query = query.join(BetParticipant).filter(
            BetParticipant.user_id == int(user_id)
        )

    # Order by created_at desc
    query = query.order_by(Bet.created_at.desc())

    bets = query.all()
    return jsonify([serialize_bet(bet, current_user_id) for bet in bets]), 200


@bets_bp.get("/my-bets")
@jwt_required()
def my_bets():
    """Get current user's bets"""
    user_id = int(get_jwt_identity())

    bets = (
        Bet.query.join(BetParticipant)
        .filter(BetParticipant.user_id == user_id)
        .order_by(Bet.created_at.desc())
        .all()
    )

    return jsonify([serialize_bet(bet, user_id) for bet in bets]), 200


@bets_bp.get("/<int:bet_id>")
@jwt_required(optional=True)
def get_bet(bet_id: int):
    """Get single bet details"""
    current_user_id = None
    identity = get_jwt_identity()
    if identity:
        current_user_id = int(identity)

    bet = Bet.query.get(bet_id)
    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    return jsonify(serialize_bet(bet, current_user_id)), 200


@bets_bp.post("/<int:bet_id>/accept")
@jwt_required()
def accept_bet(bet_id: int):
    """Accept a pending bet"""
    user_id = int(get_jwt_identity())

    bet = Bet.query.get(bet_id)
    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    # Validate bet is pending
    if bet.status != BetStatus.PENDING:
        return (
            jsonify(
                {"error": f"Bet is not pending (current status: {bet.status.value})"}
            ),
            400,
        )

    # Can't accept your own bet
    if bet.created_by == user_id:
        return jsonify({"error": "Cannot accept your own bet"}), 400

    # Check if user already accepted
    existing = BetParticipant.query.filter_by(bet_id=bet_id, user_id=user_id).first()
    if existing:
        return jsonify({"error": "You are already a participant in this bet"}), 400

    # Add acceptor as participant (acceptor always gets position_b)
    acceptor = BetParticipant()
    acceptor.bet_id = bet_id
    acceptor.user_id = user_id
    acceptor.side = "acceptor"

    db.session.add(acceptor)

    # Update bet status to active
    bet.status = BetStatus.ACTIVE
    bet.accepted_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify(serialize_bet(bet, user_id)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bets_bp.post("/<int:bet_id>/settle")
@jwt_required()
def settle_bet(bet_id: int):
    """Settle a bet by declaring a winner"""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    bet = Bet.query.get(bet_id)
    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    # Validate bet is active
    if bet.status != BetStatus.ACTIVE:
        return (
            jsonify(
                {"error": f"Bet is not active (current status: {bet.status.value})"}
            ),
            400,
        )

    # Only participants can settle (or extend this to admins later)
    participant = BetParticipant.query.filter_by(bet_id=bet_id, user_id=user_id).first()
    if not participant:
        return jsonify({"error": "Only participants can settle this bet"}), 403

    # Get winner_id from request
    winner_id = data.get("winner_id")
    outcome_notes = data.get("outcome_notes")

    if not winner_id:
        return jsonify({"error": "winner_id is required"}), 400

    winner_id = int(winner_id)

    # Validate winner is a participant
    winner_participant = BetParticipant.query.filter_by(
        bet_id=bet_id, user_id=winner_id
    ).first()
    if not winner_participant:
        return jsonify({"error": "Winner must be a participant in this bet"}), 400

    # Update bet
    bet.status = BetStatus.SETTLED
    bet.winner_id = winner_id
    bet.outcome_notes = outcome_notes
    bet.settled_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify(serialize_bet(bet, user_id)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bets_bp.post("/<int:bet_id>/cancel")
@jwt_required()
def cancel_bet(bet_id: int):
    """Cancel a bet (only if pending or by mutual agreement)"""
    user_id = int(get_jwt_identity())

    bet = Bet.query.get(bet_id)
    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    # Only creator can cancel a pending bet
    if bet.status == BetStatus.PENDING:
        if bet.created_by != user_id:
            return jsonify({"error": "Only the creator can cancel a pending bet"}), 403
    elif bet.status == BetStatus.ACTIVE:
        # For active bets, would need mutual agreement logic (future enhancement)
        return (
            jsonify(
                {
                    "error": "Active bets require mutual agreement to cancel (not yet implemented)"
                }
            ),
            400,
        )
    else:
        return (
            jsonify({"error": f"Cannot cancel bet with status: {bet.status.value}"}),
            400,
        )

    # Cancel the bet
    bet.status = BetStatus.CANCELLED

    try:
        db.session.commit()
        return jsonify(serialize_bet(bet, user_id)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

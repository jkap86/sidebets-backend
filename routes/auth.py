# backend/routes/auth.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    jwt_required,
    get_jwt_identity,
)
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password or len(password) < 6:
        return jsonify({"error": "Username and password (min 6 chars) required."}), 400

    user = User.create(username=username, password=password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username already in use."}), 409

    return jsonify({"message": "Registered successfully."}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Missing username or password."}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return jsonify({"error": "Invalid credentials."}), 401

    # identity is your primary key (user_id)
    access = create_access_token(
        identity=str(user.user_id), additional_claims={"username": user.username}
    )
    refresh = create_refresh_token(identity=str(user.user_id))

    resp = jsonify({"message": "Logged in."})
    set_access_cookies(resp, access)
    set_refresh_cookies(resp, refresh)
    return resp, 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = int(get_jwt_identity())
    access = create_access_token(identity=str(user_id))
    resp = jsonify({"message": "Access token refreshed."})
    set_access_cookies(resp, access)
    return resp, 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return (
        jsonify(
            {
                "user_id": user.user_id,
                "username": user.username,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        ),
        200,
    )


@auth_bp.post("/logout")
def logout():
    resp = jsonify({"message": "Logged out."})
    unset_jwt_cookies(resp)
    return resp, 200

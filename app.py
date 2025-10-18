from flask import Flask, render_template, send_from_directory, request
import os
from datetime import timedelta
from dotenv import load_dotenv
from extensions import db, migrate, jwt
from typing import cast
import re
from flask_cors import CORS

load_dotenv()


def create_app():

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Determine if we're in production
    is_production = os.getenv("FLASK_ENV") == "production"

    # CORS configuration
    if is_production:
        CORS(
            app,
            resources={r"/api/*": {"origins": "*"}},
            supports_credentials=True,
            allow_headers=["Content-Type", "X-CSRF-TOKEN"],
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        )
    else:
        CORS(
            app,
            resources={
                r"/api/*": {
                    "origins": re.compile(r"^http://(localhost|127\.0\.0\.1):\d+$")
                }
            },
            supports_credentials=True,
            allow_headers=["Content-Type", "X-CSRF-TOKEN"],
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        )

    # Handle OPTIONS preflight requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            return response

    # --- Config ---
    # Handle Heroku postgres:// URL format
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

    # Secure cookies only in production
    app.config["JWT_COOKIE_SECURE"] = is_production

    # --- Init ---
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from models import User

    from routes.auth import auth_bp
    from routes.bets import bets_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bets_bp, url_prefix="/api/bets")

    # Root route – serve index.html
    @app.route("/")
    def root():
        return render_template("index.html")

    # Fallback route – if it's not an API or static file, serve Flutter's index.html
    @app.route("/<path:path>")
    def fallback(path: str):
        static_dir = cast(str, app.static_folder)
        try:
            return send_from_directory(static_dir, path)
        except Exception:
            return render_template("index.html")

    return app


# --- Entry point when running locally ---
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
else:
    # For gunicorn in production
    app = create_app()

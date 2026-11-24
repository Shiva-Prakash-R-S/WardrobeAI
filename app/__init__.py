from flask import Flask
from app.config import config_by_name
from app.extensions import db, migrate, jwt, cors
from app.routes.auth import auth_bp
from app.routes.profile import profile_bp
from app.routes.clothing import clothing_bp
from app.routes.recommendation import recommendation_bp
from app.routes.body_profile import body_profile_bp
from app.routes.tryon import tryon_bp
from app.services.auth_service import AuthService
from app.utils.response import error_response

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # JWT Blocklist checking for server-side token revocation
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload: dict):
        return AuthService.is_token_revoked(jwt_payload)

    # JWT Error handlers formatted in standard envelope
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return error_response("Token has been revoked. Please log in again.", status_code=401)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return error_response("Token has expired. Please refresh your session.", status_code=401)

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return error_response(f"Invalid authentication token: {error}", status_code=401)

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return error_response("Authentication token is missing. Please log in.", status_code=401)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(clothing_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(body_profile_bp)
    app.register_blueprint(tryon_bp)

    # Root health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return {
            "success": True,
            "status": "healthy",
            "service": "Wardrobe AI Backend",
            "version": "1.0.0"
        }, 200

    # Global HTTP error handlers
    @app.errorhandler(404)
    def not_found(error):
        return error_response("Requested endpoint does not exist", status_code=404)

    @app.errorhandler(413)
    def request_too_large(error):
        return error_response("File size exceeds the 10MB limit.", status_code=413)

    @app.errorhandler(500)
    def internal_error(error):
        return error_response("Internal server error", status_code=500)

    # CLI Commands
    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Seed or synchronize default demo account."""
        from seed_demo_user import seed_demo_account
        seed_demo_account()

    return app


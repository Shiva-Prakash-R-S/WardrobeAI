from flask import Blueprint, request
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
    create_access_token
)
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from app.utils.response import success_response, error_response
from app.utils.validators import validate_registration_input, validate_login_input

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    is_valid, validation_error = validate_registration_input(data)
    if not is_valid:
        return error_response(validation_error, status_code=400)

    user_data, error = AuthService.register_user(
        username=data["username"].strip(),
        email=data["email"].strip(),
        password=data["password"],
        full_name=data["full_name"].strip()
    )

    if error:
        status_code = 409 if "already" in error else 400
        return error_response(error, status_code=status_code)

    return success_response(
        message="Account created successfully",
        data={"user": user_data},
        status_code=201
    )

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    is_valid, validation_error = validate_login_input(data)
    if not is_valid:
        return error_response(validation_error, status_code=400)

    auth_data, error = AuthService.authenticate_user(
        email=data["email"].strip(),
        password=data["password"]
    )

    if error:
        return error_response(error, status_code=401)

    return success_response(
        message="Login successful",
        data=auth_data,
        status_code=200
    )

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)
    return success_response(
        message="Token refreshed successfully",
        data={"access_token": new_access_token},
        status_code=200
    )

@auth_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    token_type = jwt_data["type"]
    user_id = int(jwt_data["sub"])
    exp_timestamp = jwt_data["exp"]

    revoked = AuthService.revoke_token(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        exp_timestamp=exp_timestamp
    )

    if not revoked:
        return error_response("Failed to revoke session token", status_code=500)

    return success_response(
        message="Successfully logged out and session revoked",
        status_code=200
    )

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    current_user_id = int(get_jwt_identity())
    profile_data, error = ProfileService.get_profile_by_user_id(current_user_id)
    if error:
        return error_response(error, status_code=404)

    return success_response(
        message="Current user profile retrieved successfully",
        data={"user": profile_data},
        status_code=200
    )


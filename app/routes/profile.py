from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.profile_service import ProfileService
from app.utils.response import success_response, error_response

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")

@profile_bp.route("", methods=["GET"])
@jwt_required()
def get_profile():
    current_user_id = int(get_jwt_identity())
    profile_data, error = ProfileService.get_profile_by_user_id(current_user_id)
    if error:
        return error_response(error, status_code=404)

    return success_response(
        message="Profile retrieved successfully",
        data={"profile": profile_data},
        status_code=200
    )

@profile_bp.route("", methods=["PUT"])
@jwt_required()
def update_profile():
    current_user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    updated_profile, error = ProfileService.update_profile(current_user_id, data)
    if error:
        return error_response(error, status_code=400)

    return success_response(
        message="Profile updated successfully",
        data={"profile": updated_profile},
        status_code=200
    )


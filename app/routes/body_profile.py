import os
from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from app.services.body_profile_service import BodyProfileService
from app.services.image_service import ImageStorageService
from app.models.body_profile import UserBodyProfile
from app.utils.response import success_response, error_response

body_profile_bp = Blueprint("body_profile", __name__, url_prefix="/api/body-profile")


@body_profile_bp.route("", methods=["POST"])
@jwt_required()
def upload_or_update_body_profile():
    """
    POST /api/body-profile
    Multipart form-data:
      - image: File (optional if profile already exists and only updating metrics)
      - height_cm: Float (optional)
      - weight_kg: Float (optional)
      - body_shape: String (optional)
      - skin_tone: String (optional)
      - gender: String (optional)
    """
    user_id = int(get_jwt_identity())
    form_data = request.form.to_dict()
    file = request.files.get("image")

    res, status_code = BodyProfileService.create_or_update_body_profile(user_id, form_data, file)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], res.get("body_profile"), status_code)


@body_profile_bp.route("", methods=["GET"])
@jwt_required()
def get_body_profile():
    """
    GET /api/body-profile
    Retrieve active body profile for authenticated user.
    """
    user_id = int(get_jwt_identity())
    profile = BodyProfileService.get_body_profile(user_id)
    if not profile:
        return error_response("No body profile found. Please upload a full-body photograph.", 404)

    return success_response("Body profile retrieved successfully.", profile.to_dict(), 200)


@body_profile_bp.route("", methods=["DELETE"])
@jwt_required()
def delete_body_profile():
    """
    DELETE /api/body-profile
    Deletes body profile and photograph.
    """
    user_id = int(get_jwt_identity())
    res, status_code = BodyProfileService.delete_body_profile(user_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], None, status_code)


@body_profile_bp.route("/images/<filename>", methods=["GET"])
def get_body_image(filename: str):
    """
    GET /api/body-profile/images/<filename>
    Protected image retrieval.
    Accepts Bearer token in Authorization header or ?token=<token> in query params.
    Enforces strict user isolation: only the owner may view their body photograph.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif request.args.get("token"):
        token = request.args.get("token")

    if not token:
        return error_response("Authentication token required to view private body photographs.", 401)

    try:
        decoded = decode_token(token)
        user_id = int(decoded["sub"])
    except Exception:
        return error_response("Invalid or expired authentication token.", 401)

    clean_name = os.path.basename(filename)
    search_pattern = f"%{clean_name}"

    profile = UserBodyProfile.query.filter(
        (UserBodyProfile.photo_url.like(search_pattern)) |
        (UserBodyProfile.thumbnail_url.like(search_pattern))
    ).first()

    if not profile:
        file_path = ImageStorageService.get_body_image_path(clean_name)
        if not file_path:
            return error_response("Photograph not found.", 404)
        return error_response("Profile record not found.", 404)

    if profile.user_id != user_id:
        return error_response("Access denied. You do not own this private photograph.", 403)

    file_path = ImageStorageService.get_body_image_path(clean_name)
    if not file_path or not os.path.isfile(file_path):
        return error_response("Photograph file not found on disk.", 404)

    return send_file(file_path, mimetype="image/jpeg")

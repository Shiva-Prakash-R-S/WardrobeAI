import os
from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from app.services.tryon_service import VirtualTryOnService
from app.services.image_service import ImageStorageService
from app.models.tryon import VirtualTryOnResult
from app.utils.response import success_response, error_response

tryon_bp = Blueprint("tryon", __name__, url_prefix="/api/tryon")


@tryon_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_tryon():
    """
    POST /api/tryon/generate
    JSON body:
    {
        "clothing_item_ids": [1, 2],
        "body_profile_id": 1,   # optional
        "notes": "Styling notes" # optional
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    clothing_item_ids = data.get("clothing_item_ids")
    if not clothing_item_ids or not isinstance(clothing_item_ids, list):
        return error_response("Please provide a list of clothing_item_ids.", 400)

    body_profile_id = data.get("body_profile_id")
    notes = data.get("notes")

    res, status_code = VirtualTryOnService.create_tryon_job(
        user_id=user_id,
        clothing_item_ids=clothing_item_ids,
        body_profile_id=body_profile_id,
        notes=notes
    )
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], res, status_code)


@tryon_bp.route("/jobs/<job_id>", methods=["GET"])
@jwt_required()
def get_job_status(job_id: str):
    """
    GET /api/tryon/jobs/<job_id>
    Check processing status and progress of a try-on job.
    """
    user_id = int(get_jwt_identity())
    res, status_code = VirtualTryOnService.get_job_status(user_id, job_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response("Job status retrieved.", res.get("job"), status_code)


@tryon_bp.route("/results/<int:result_id>", methods=["GET"])
@jwt_required()
def get_result(result_id: int):
    """
    GET /api/tryon/results/<result_id>
    Retrieve a completed try-on result by ID.
    """
    user_id = int(get_jwt_identity())
    res, status_code = VirtualTryOnService.get_result_by_id(user_id, result_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response("Virtual try-on result retrieved.", res.get("result"), status_code)


@tryon_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    """
    GET /api/tryon/history
    Query params:
      page: int (default 1)
      per_page: int (default 20)
      favorites: bool (default False)
    """
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    favorites_param = request.args.get("favorites", "false").lower() in ("true", "1")

    res, status_code = VirtualTryOnService.list_history(
        user_id=user_id,
        page=page,
        per_page=per_page,
        only_favorites=favorites_param
    )
    return success_response("Virtual try-on history retrieved.", res, status_code)


@tryon_bp.route("/results/<int:result_id>/favorite", methods=["POST"])
@jwt_required()
def toggle_favorite(result_id: int):
    """
    POST /api/tryon/results/<result_id>/favorite
    Toggle favorite status for this try-on result.
    """
    user_id = int(get_jwt_identity())
    res, status_code = VirtualTryOnService.toggle_favorite(user_id, result_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], res, status_code)


@tryon_bp.route("/results/<int:result_id>", methods=["DELETE"])
@jwt_required()
def delete_result(result_id: int):
    """
    DELETE /api/tryon/results/<result_id>
    Delete virtual try-on result and stored image.
    """
    user_id = int(get_jwt_identity())
    res, status_code = VirtualTryOnService.delete_result(user_id, result_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], None, status_code)


@tryon_bp.route("/images/<filename>", methods=["GET"])
def get_tryon_image(filename: str):
    """
    GET /api/tryon/images/<filename>
    Protected endpoint serving generated try-on result images.
    Enforces JWT authentication and verifies user ownership.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif request.args.get("token"):
        token = request.args.get("token")

    if not token:
        return error_response("Authentication token required to view virtual try-on preview.", 401)

    try:
        decoded = decode_token(token)
        user_id = int(decoded["sub"])
    except Exception:
        return error_response("Invalid or expired authentication token.", 401)

    clean_name = os.path.basename(filename)
    search_pattern = f"%{clean_name}"

    result = VirtualTryOnResult.query.filter(
        VirtualTryOnResult.result_image_url.like(search_pattern)
    ).first()

    if not result:
        file_path = ImageStorageService.get_tryon_image_path(clean_name)
        if not file_path:
            return error_response("Preview image not found.", 404)
        return error_response("Preview record not found.", 404)

    if result.user_id != user_id:
        return error_response("Access denied. You do not own this virtual try-on preview.", 403)

    file_path = ImageStorageService.get_tryon_image_path(clean_name)
    if not file_path or not os.path.isfile(file_path):
        return error_response("Preview image file not found on disk.", 404)

    return send_file(file_path, mimetype="image/jpeg")

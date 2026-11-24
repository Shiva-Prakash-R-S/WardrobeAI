import os
from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from app.services.clothing_service import ClothingService
from app.services.image_service import ImageStorageService, ImageValidationError
from app.services.color_service import ColorService
from app.models.clothing_item import ClothingItem
from app.utils.response import success_response, error_response

clothing_bp = Blueprint("clothing", __name__, url_prefix="/api/clothing")


@clothing_bp.route("", methods=["POST"])
@jwt_required()
def add_clothing():
    """
    POST /api/clothing
    Content-Type: multipart/form-data
    Upload image and create a new clothing item for the authenticated user.
    """
    user_id = int(get_jwt_identity())
    form_data = request.form.to_dict()
    file = request.files.get("image")

    res, status_code = ClothingService.create_clothing(user_id, form_data, file)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], res["clothing_item"], status_code)


@clothing_bp.route("", methods=["GET"])
@jwt_required()
def list_clothing():
    """
    GET /api/clothing
    List authenticated user's clothing with filtering, search, and pagination.
    """
    user_id = int(get_jwt_identity())

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category", type=str)
    subcategory = request.args.get("subcategory", type=str)
    color = request.args.get("color", type=str)
    q = request.args.get("q", type=str)
    sort_by = request.args.get("sort_by", "created_at", type=str)
    order = request.args.get("order", "desc", type=str)

    data = ClothingService.get_user_clothing(
        user_id=user_id,
        page=page,
        per_page=per_page,
        category=category,
        subcategory=subcategory,
        color=color,
        q=q,
        sort_by=sort_by,
        order=order
    )
    return success_response("Clothing items retrieved successfully.", data, 200)


@clothing_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_clothing_summary():
    """
    GET /api/clothing/summary
    Return category counts and total availability for the authenticated user.
    """
    user_id = int(get_jwt_identity())
    summary = ClothingService.get_clothing_summary(user_id)
    return success_response("Clothing summary retrieved successfully.", summary, 200)


@clothing_bp.route("/detect-colors", methods=["POST"])
@jwt_required()
def detect_colors():
    """
    POST /api/clothing/detect-colors
    Content-Type: multipart/form-data
    Detect dominant colors from uploaded clothing photo.
    """
    file = request.files.get("image")
    if not file:
        return error_response("Image file is required for color detection.", 400)

    try:
        image = ImageStorageService.validate_and_open_image(file)
        result = ColorService.detect_dominant_colors(image)
        return success_response("Dominant colors detected successfully.", result, 200)
    except ImageValidationError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f"Failed to analyze image colors: {str(e)}", 500)


@clothing_bp.route("/<int:item_id>", methods=["GET"])
@jwt_required()
def get_clothing_details(item_id: int):
    """
    GET /api/clothing/<id>
    Retrieve full details for a clothing item owned by the user.
    """
    user_id = int(get_jwt_identity())
    res, status_code = ClothingService.get_clothing_by_id(item_id, user_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response("Clothing item details retrieved successfully.", res["clothing_item"], 200)


@clothing_bp.route("/<int:item_id>", methods=["PUT"])
@jwt_required()
def update_clothing(item_id: int):
    """
    PUT /api/clothing/<id>
    Update clothing metadata fields.
    """
    user_id = int(get_jwt_identity())
    update_data = request.get_json(silent=True) or request.form.to_dict()

    res, status_code = ClothingService.update_clothing(item_id, user_id, update_data)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], res["clothing_item"], 200)


@clothing_bp.route("/<int:item_id>/image", methods=["PATCH"])
@jwt_required()
def replace_clothing_image(item_id: int):
    """
    PATCH /api/clothing/<id>/image
    Replace the photo of an existing clothing item.
    """
    user_id = int(get_jwt_identity())
    file = request.files.get("image")
    if not file:
        return error_response("Replacement image file is required.", 400)

    res, status_code = ClothingService.replace_clothing_image(item_id, user_id, file)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], res["clothing_item"], 200)


@clothing_bp.route("/<int:item_id>", methods=["DELETE"])
@jwt_required()
def delete_clothing(item_id: int):
    """
    DELETE /api/clothing/<id>
    Delete clothing item and associated image files.
    """
    user_id = int(get_jwt_identity())
    res, status_code = ClothingService.delete_clothing(item_id, user_id)
    if status_code >= 400:
        return error_response(res["message"], status_code)
    return success_response(res["message"], None, 200)


@clothing_bp.route("/images/<path:filename>", methods=["GET"])
def get_clothing_image(filename: str):
    """
    GET /api/clothing/images/<filename>
    Securely serves clothing image files.
    Requires authentication either via Authorization Bearer header or ?token= query parameter.
    Enforces user ownership so User A cannot download User B's images.
    """
    # Extract JWT from Authorization header or ?token= query parameter
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "token" in request.args:
        token = request.args.get("token")

    if not token:
        return error_response("Authentication required to access clothing images.", 401)

    try:
        decoded = decode_token(token)
        user_id = int(decoded["sub"])
    except Exception:
        return error_response("Invalid or expired authentication token.", 401)

    # Sanitize requested filename against directory traversal
    clean_name = os.path.basename(filename)

    # Verify ownership: check that this filename belongs to a clothing item owned by user_id
    search_pattern = f"%{clean_name}"
    item = ClothingItem.query.filter(
        (ClothingItem.image_url.like(search_pattern)) |
        (ClothingItem.thumbnail_url.like(search_pattern))
    ).first()

    if not item:
        # Check if file exists on disk
        file_path = ImageStorageService.get_image_file_path(clean_name)
        if not file_path:
            return error_response("Image file not found.", 404)
        return error_response("Image record not found.", 404)

    if item.user_id != user_id:
        return error_response("Access denied. You do not own this clothing image.", 403)

    file_path = ImageStorageService.get_image_file_path(clean_name)
    if not file_path or not os.path.isfile(file_path):
        return error_response("Image file not found on disk.", 404)

    return send_file(file_path, mimetype="image/jpeg")


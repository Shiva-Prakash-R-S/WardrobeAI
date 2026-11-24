from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.recommendation_service import RecommendationService, OCCASIONS
from app.utils.response import success_response, error_response

recommendation_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


@recommendation_bp.route("/occasions", methods=["GET"])
@jwt_required()
def get_occasions():
    """
    GET /api/recommendations/occasions
    Retrieve the standard list of 10 supported style occasions.
    """
    return success_response("Occasions retrieved successfully.", {"occasions": OCCASIONS}, 200)


@recommendation_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_recommendations():
    """
    POST /api/recommendations/generate
    Generate ranked outfit combinations based on occasion, color harmony, and style compatibility.
    Body:
    {
        "occasion": "Office",
        "limit": 5
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    occasion = data.get("occasion", "Casual")
    if not isinstance(occasion, str):
        return error_response("Field 'occasion' must be a string.", 400)

    try:
        limit = int(data.get("limit", 5))
        if limit < 1 or limit > 20:
            limit = 5
    except (ValueError, TypeError):
        limit = 5

    result = RecommendationService.generate_recommendations(
        user_id=user_id,
        occasion=occasion,
        limit=limit
    )

    if not result.get("can_generate"):
        return success_response(result["message"], result, 200)

    return success_response(result["message"], result, 201)


@recommendation_bp.route("/<int:rec_id>", methods=["GET"])
@jwt_required()
def get_recommendation_details(rec_id: int):
    """
    GET /api/recommendations/<id>
    Retrieve full details of a specific outfit recommendation.
    """
    user_id = int(get_jwt_identity())
    rec = RecommendationService.get_recommendation_by_id(user_id, rec_id)

    if not rec:
        return error_response("Recommendation not found or access denied.", 404)

    return success_response("Recommendation retrieved successfully.", rec, 200)


@recommendation_bp.route("/history", methods=["GET"])
@jwt_required()
def get_recommendation_history():
    """
    GET /api/recommendations/history
    Retrieve paginated recommendation history for the authenticated user.
    Query params: page, per_page, occasion
    """
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    occasion = request.args.get("occasion", type=str)

    history = RecommendationService.get_history(
        user_id=user_id,
        page=page,
        per_page=per_page,
        occasion=occasion
    )

    return success_response("Recommendation history retrieved successfully.", history, 200)


@recommendation_bp.route("/<int:rec_id>/favorite", methods=["POST"])
@jwt_required()
def add_favorite_outfit(rec_id: int):
    """
    POST /api/recommendations/<id>/favorite
    Mark an outfit recommendation as favorite.
    """
    user_id = int(get_jwt_identity())
    rec = RecommendationService.set_favorite(user_id, rec_id, is_favorite=True)

    if not rec:
        return error_response("Recommendation not found or access denied.", 404)

    return success_response("Outfit saved to favorites.", rec, 200)


@recommendation_bp.route("/<int:rec_id>/favorite", methods=["DELETE"])
@jwt_required()
def remove_favorite_outfit(rec_id: int):
    """
    DELETE /api/recommendations/<id>/favorite
    Remove an outfit recommendation from favorites.
    """
    user_id = int(get_jwt_identity())
    rec = RecommendationService.set_favorite(user_id, rec_id, is_favorite=False)

    if not rec:
        return error_response("Recommendation not found or access denied.", 404)

    return success_response("Outfit removed from favorites.", rec, 200)


@recommendation_bp.route("/favorites", methods=["GET"])
@jwt_required()
def get_favorite_outfits():
    """
    GET /api/recommendations/favorites
    Retrieve user's favorite outfits.
    Query params: page, per_page
    """
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    favorites = RecommendationService.get_favorites(
        user_id=user_id,
        page=page,
        per_page=per_page
    )

    return success_response("Favorite outfits retrieved successfully.", favorites, 200)

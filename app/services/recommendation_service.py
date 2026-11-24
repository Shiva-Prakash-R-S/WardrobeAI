from typing import Dict, Any, List, Optional, Tuple
from app.extensions import db
from app.models.clothing_item import ClothingItem
from app.models.recommendation import Recommendation, RecommendationItem
from app.services.color_compatibility import ColorCompatibilityService

# 10 Supported Occasions
OCCASIONS = [
    "College",
    "Office",
    "Casual",
    "Formal",
    "Party",
    "Wedding",
    "Interview",
    "Date",
    "Travel",
    "Sports / Gym"
]

# Occasion rules mapping subcategories to suitability scores
# Score weights: Preferred (100), Acceptable (75), Marginal (45), Incompatible (10)
OCCASION_RULES: Dict[str, Dict[str, Any]] = {
    "Formal": {
        "preferred": {
            "Formal shirts", "Jackets", "Formal trousers", "Formal shoes", "Loafers", "Belts", "Watches"
        },
        "acceptable": {
            "Sweaters", "Chinos", "Casual trousers"
        },
        "incompatible": {
            "T-shirts", "Hoodies", "Sweatshirts", "Shorts", "Joggers", "Sandals", "Caps"
        },
        "vibe": "Impeccably tailored formal presentation"
    },
    "Interview": {
        "preferred": {
            "Formal shirts", "Jackets", "Formal trousers", "Chinos", "Formal shoes", "Loafers", "Belts", "Watches"
        },
        "acceptable": {
            "Sweaters", "Casual trousers"
        },
        "incompatible": {
            "T-shirts", "Hoodies", "Sweatshirts", "Shorts", "Joggers", "Sandals", "Caps", "Sunglasses"
        },
        "vibe": "Professional, credible, and polished career attire"
    },
    "Office": {
        "preferred": {
            "Formal shirts", "Polo T-shirts", "Casual shirts", "Sweaters", "Jackets",
            "Formal trousers", "Chinos", "Casual trousers", "Formal shoes", "Loafers", "Watches", "Belts"
        },
        "acceptable": {
            "Jeans", "Casual shoes", "Sneakers"
        },
        "incompatible": {
            "Shorts", "Joggers", "Hoodies", "Sandals", "Caps"
        },
        "vibe": "Refined business-casual elegance"
    },
    "Wedding": {
        "preferred": {
            "Formal shirts", "Jackets", "Formal trousers", "Formal shoes", "Loafers", "Watches", "Belts"
        },
        "acceptable": {
            "Chinos", "Sweaters"
        },
        "incompatible": {
            "T-shirts", "Hoodies", "Sweatshirts", "Jeans", "Shorts", "Joggers", "Sandals", "Caps", "Sneakers"
        },
        "vibe": "Celebratory, sophisticated ceremonial elegance"
    },
    "College": {
        "preferred": {
            "T-shirts", "Polo T-shirts", "Casual shirts", "Hoodies", "Sweatshirts", "Jackets",
            "Jeans", "Chinos", "Casual trousers", "Joggers", "Sneakers", "Casual shoes", "Caps", "Watches"
        },
        "acceptable": {
            "Shorts", "Sandals", "Loafers", "Sweaters", "Formal shirts", "Sunglasses", "Bracelets"
        },
        "incompatible": {
            "Formal shoes"
        },
        "vibe": "Youthful, versatile, and relaxed campus style"
    },
    "Casual": {
        "preferred": {
            "T-shirts", "Polo T-shirts", "Casual shirts", "Hoodies", "Sweatshirts", "Jackets", "Sweaters",
            "Jeans", "Chinos", "Casual trousers", "Shorts", "Joggers", "Sneakers", "Casual shoes", "Loafers",
            "Sunglasses", "Watches", "Caps"
        },
        "acceptable": {
            "Sandals", "Boots", "Formal shirts", "Formal trousers"
        },
        "incompatible": set(),
        "vibe": "Effortless, comfortable weekend aesthetics"
    },
    "Party": {
        "preferred": {
            "Casual shirts", "Jackets", "Polo T-shirts", "T-shirts", "Sweaters",
            "Jeans", "Chinos", "Casual trousers", "Formal trousers", "Loafers", "Boots", "Casual shoes", "Watches", "Bracelets"
        },
        "acceptable": {
            "Formal shirts", "Sneakers", "Belts", "Sunglasses"
        },
        "incompatible": {
            "Shorts", "Joggers", "Sandals"
        },
        "vibe": "Sharp, charismatic evening party atmosphere"
    },
    "Date": {
        "preferred": {
            "Casual shirts", "Formal shirts", "Polo T-shirts", "Sweaters", "Jackets",
            "Chinos", "Jeans", "Casual trousers", "Loafers", "Boots", "Casual shoes", "Watches", "Belts"
        },
        "acceptable": {
            "Formal trousers", "Sneakers", "T-shirts", "Sunglasses"
        },
        "incompatible": {
            "Joggers", "Shorts", "Sandals", "Caps"
        },
        "vibe": "Thoughtful, attractive, and subtly charming date attire"
    },
    "Travel": {
        "preferred": {
            "T-shirts", "Polo T-shirts", "Casual shirts", "Hoodies", "Sweatshirts", "Jackets",
            "Joggers", "Chinos", "Jeans", "Casual trousers", "Shorts", "Sneakers", "Casual shoes",
            "Sunglasses", "Caps", "Watches"
        },
        "acceptable": {
            "Sandals", "Boots", "Sweaters"
        },
        "incompatible": {
            "Formal shirts", "Formal trousers", "Formal shoes"
        },
        "vibe": "Comfortable, mobile transit and exploratory utility"
    },
    "Sports / Gym": {
        "preferred": {
            "T-shirts", "Polo T-shirts", "Sweatshirts", "Hoodies",
            "Joggers", "Shorts", "Sneakers", "Caps", "Watches"
        },
        "acceptable": {
            "Casual shirts"
        },
        "incompatible": {
            "Formal shirts", "Jackets", "Sweaters", "Formal trousers", "Jeans", "Chinos",
            "Formal shoes", "Loafers", "Boots", "Sandals", "Belts"
        },
        "vibe": "High-performance athletic agility and active comfort"
    }
}

# Style archetype cohesion matrix
FORMAL_SUBCATS = {"Formal shirts", "Jackets", "Formal trousers", "Formal shoes", "Loafers"}
CASUAL_SUBCATS = {"Casual shirts", "Polo T-shirts", "T-shirts", "Jeans", "Chinos", "Casual trousers", "Sneakers", "Casual shoes"}
STREET_ATHLETIC = {"Hoodies", "Sweatshirts", "Joggers", "Shorts", "Sneakers", "Caps"}


class RecommendationService:
    """
    Intelligent outfit recommendation and styling service.
    Analyzes personal wardrobe collections to generate harmonized, occasion-specific outfits.
    """

    @classmethod
    def evaluate_item_occasion(cls, item: ClothingItem, occasion: str) -> int:
        """
        Evaluate individual item suitability for an occasion (0 - 100).
        """
        rules = OCCASION_RULES.get(occasion, OCCASION_RULES["Casual"])
        subcat = item.subcategory or ""
        cat = item.category or ""

        if subcat in rules["incompatible"] or cat in rules["incompatible"]:
            return 15
        if subcat in rules["preferred"]:
            return 100
        if subcat in rules["acceptable"]:
            return 75

        # If user explicitly tagged the item with this occasion during upload
        if item.occasion and item.occasion.lower() == occasion.lower():
            return 95

        return 60

    @classmethod
    def evaluate_style_cohesion(
        cls,
        top: ClothingItem,
        bottom: ClothingItem,
        footwear: Optional[ClothingItem] = None
    ) -> Tuple[int, str]:
        """
        Evaluate aesthetic silhouette and subcategory harmony (0 - 100).
        """
        top_sub = top.subcategory or ""
        bot_sub = bottom.subcategory or ""
        foot_sub = footwear.subcategory if footwear else ""

        # Strong formal alignment
        if top_sub in FORMAL_SUBCATS and bot_sub in {"Formal trousers", "Chinos"}:
            if not footwear or foot_sub in {"Formal shoes", "Loafers"}:
                return 98, "Classic sartorial symmetry with tailored lines."
            return 80, "Slightly dressed-down tailored silhouette."

        # Clashing formal top with athletic bottoms
        if top_sub == "Formal shirts" and bot_sub in {"Joggers", "Shorts"}:
            return 30, "Aesthetic clash between structured shirting and athletic leisure."

        # Athletic synergy
        if top_sub in STREET_ATHLETIC and bot_sub in STREET_ATHLETIC:
            return 95, "Consistent sporty streetwear silhouette."

        # Smart-casual synergy (Polo/Casual shirt + Chinos/Jeans)
        if top_sub in {"Casual shirts", "Polo T-shirts", "Sweaters"} and bot_sub in {"Chinos", "Jeans", "Casual trousers"}:
            return 94, "Quintessential smart-casual harmony with relaxed sophistication."

        # Everyday casual
        if top_sub in {"T-shirts", "Casual shirts"} and bot_sub in {"Jeans", "Shorts", "Chinos"}:
            return 90, "Easy everyday balance of relaxed staples."

        return 75, "Versatile, balanced garment pairing."

    @classmethod
    def generate_recommendations(
        cls,
        user_id: int,
        occasion: str = "Casual",
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Generate, score, and persist ranked outfit recommendations for the authenticated user.
        """
        # Validate occasion
        valid_occasion = occasion.strip()
        matched_occasion = next(
            (o for o in OCCASIONS if o.lower() == valid_occasion.lower()),
            "Casual"
        )

        # 1. Fetch user's active clothing items
        user_items = ClothingItem.query.filter_by(
            user_id=user_id,
            is_available=True
        ).order_by(ClothingItem.created_at.desc()).all()

        if not user_items:
            return {
                "can_generate": False,
                "message": "Your wardrobe is empty. Add clothing items to receive AI outfit recommendations.",
                "total_items": 0,
                "recommendations": []
            }

        # Segregate by primary categories
        tops = [item for item in user_items if (item.category or "").lower() == "tops"]
        bottoms = [item for item in user_items if (item.category or "").lower() == "bottoms"]
        footwear_list = [item for item in user_items if (item.category or "").lower() == "footwear"]
        accessories = [item for item in user_items if (item.category or "").lower() == "accessories"]

        if not tops or not bottoms:
            missing = []
            if not tops:
                missing.append("Tops (shirts, t-shirts, etc.)")
            if not bottoms:
                missing.append("Bottoms (trousers, jeans, chinos)")
            return {
                "can_generate": False,
                "message": f"To generate outfit recommendations, your wardrobe needs at least one Top and one Bottom. Missing: {', '.join(missing)}.",
                "total_items": len(user_items),
                "recommendations": []
            }

        candidate_outfits: List[Dict[str, Any]] = []

        # 2. Iterate combinations
        # We pair Tops and Bottoms, and optionally Footwear and Accessories
        for top in tops:
            for bottom in bottoms:
                # Basic check: do not pair identical items (sanity check)
                if top.id == bottom.id:
                    continue

                # Determine candidates with footwear
                footwear_options = footwear_list if footwear_list else [None]

                for foot in footwear_options:
                    # Select best complementing accessory if available
                    chosen_accessory: Optional[ClothingItem] = None
                    if accessories:
                        best_acc_score = -1
                        for acc in accessories:
                            # Accessories match rule: favor accessories suited for occasion
                            acc_occ_score = cls.evaluate_item_occasion(acc, matched_occasion)
                            if acc_occ_score > best_acc_score:
                                best_acc_score = acc_occ_score
                                chosen_accessory = acc

                    # 3. Compute Individual Scoring Factors
                    # A. Color Compatibility Score (35%)
                    foot_color = (foot.primary_color, foot.color_hex) if foot else None
                    acc_color = (chosen_accessory.primary_color, chosen_accessory.color_hex) if chosen_accessory else None
                    color_eval = ColorCompatibilityService.evaluate_outfit_colors(
                        top_color=(top.primary_color, top.color_hex),
                        bottom_color=(bottom.primary_color, bottom.color_hex),
                        footwear_color=foot_color,
                        accessory_color=acc_color
                    )
                    color_score = color_eval["score"]

                    # B. Occasion Suitability Score (35%)
                    top_occ = cls.evaluate_item_occasion(top, matched_occasion)
                    bot_occ = cls.evaluate_item_occasion(bottom, matched_occasion)
                    if foot:
                        foot_occ = cls.evaluate_item_occasion(foot, matched_occasion)
                        occasion_score = int(round(top_occ * 0.40 + bot_occ * 0.40 + foot_occ * 0.20))
                    else:
                        occasion_score = int(round(top_occ * 0.50 + bot_occ * 0.50))

                    # C. Style Cohesion Score (15%)
                    style_score, style_note = cls.evaluate_style_cohesion(top, bottom, foot)

                    # D. Category Completeness Score (15%)
                    if foot and chosen_accessory:
                        completeness_score = 100
                    elif foot:
                        completeness_score = 90
                    else:
                        completeness_score = 65

                    # Weighted Overall Score (0 - 100)
                    overall_score = int(round(
                        color_score * 0.35 +
                        occasion_score * 0.35 +
                        style_score * 0.15 +
                        completeness_score * 0.15
                    ))
                    overall_score = max(0, min(100, overall_score))

                    # Title generation
                    top_col = top.primary_color or "Sleek"
                    bot_col = bottom.primary_color or "Tonal"
                    outfit_title = f"{top_col} & {bot_col} {matched_occasion} Ensemble"

                    # Explanations
                    explanation_parts = [
                        f"{color_eval['explanation']}",
                        f"Tailored for {matched_occasion}: {style_note}"
                    ]
                    if not foot:
                        explanation_parts.append("Note: Pair with neutral sneakers or loafers to complete this look.")
                    elif chosen_accessory:
                        explanation_parts.append(f"Accented with {chosen_accessory.name} for subtle refinement.")

                    full_explanation = " ".join(explanation_parts)

                    candidate_outfits.append({
                        "user_id": user_id,
                        "occasion": matched_occasion,
                        "title": outfit_title,
                        "compatibility_score": overall_score,
                        "color_score": color_score,
                        "occasion_score": occasion_score,
                        "style_score": style_score,
                        "completeness_score": completeness_score,
                        "explanation": full_explanation,
                        "top": top,
                        "bottom": bottom,
                        "footwear": foot,
                        "accessory": chosen_accessory
                    })

        # 4. Filter and diversify
        # Exclude outfits with extremely poor occasion suitability (e.g. gym shorts at formal events)
        # unless total candidates are very few
        filtered = [c for c in candidate_outfits if c["occasion_score"] >= 40]
        if not filtered:
            filtered = candidate_outfits

        # Sort by overall score descending
        filtered.sort(key=lambda x: x["compatibility_score"], reverse=True)

        # Deduplication & diversity promotion:
        # Keep unique combinations of (top.id, bottom.id, footwear.id)
        selected_outfits: List[Dict[str, Any]] = []
        seen_keys = set()
        top_counts: Dict[int, int] = {}

        for cand in filtered:
            key = (
                cand["top"].id,
                cand["bottom"].id,
                cand["footwear"].id if cand["footwear"] else None,
                cand["accessory"].id if cand["accessory"] else None
            )
            if key in seen_keys:
                continue

            top_id = cand["top"].id
            # Allow max 2 outfits sharing the same top if we have enough variety
            if len(filtered) > limit and top_counts.get(top_id, 0) >= 2:
                continue

            seen_keys.add(key)
            top_counts[top_id] = top_counts.get(top_id, 0) + 1
            selected_outfits.append(cand)

            if len(selected_outfits) >= limit:
                break

        # 5. Persist recommendations into database
        persisted_records: List[Recommendation] = []
        for out in selected_outfits:
            rec = Recommendation(
                user_id=user_id,
                occasion=out["occasion"],
                title=out["title"],
                compatibility_score=out["compatibility_score"],
                color_score=out["color_score"],
                occasion_score=out["occasion_score"],
                completeness_score=out["completeness_score"],
                style_score=out["style_score"],
                explanation=out["explanation"],
                is_favorite=False
            )
            db.session.add(rec)
            db.session.flush()  # populate rec.id

            # Add RecommendationItem records
            db.session.add(RecommendationItem(
                recommendation_id=rec.id,
                clothing_item_id=out["top"].id,
                role="top"
            ))
            db.session.add(RecommendationItem(
                recommendation_id=rec.id,
                clothing_item_id=out["bottom"].id,
                role="bottom"
            ))
            if out["footwear"]:
                db.session.add(RecommendationItem(
                    recommendation_id=rec.id,
                    clothing_item_id=out["footwear"].id,
                    role="footwear"
                ))
            if out["accessory"]:
                db.session.add(RecommendationItem(
                    recommendation_id=rec.id,
                    clothing_item_id=out["accessory"].id,
                    role="accessory"
                ))

            persisted_records.append(rec)

        db.session.commit()

        return {
            "can_generate": True,
            "message": f"Successfully generated {len(persisted_records)} outfit recommendations for {matched_occasion}.",
            "occasion": matched_occasion,
            "total_items": len(user_items),
            "recommendations": [rec.to_dict() for rec in persisted_records]
        }

    @classmethod
    def get_recommendation_by_id(cls, user_id: int, rec_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific recommendation ensuring user ownership."""
        rec = Recommendation.query.filter_by(id=rec_id, user_id=user_id).first()
        return rec.to_dict() if rec else None

    @classmethod
    def get_history(
        cls,
        user_id: int,
        page: int = 1,
        per_page: int = 10,
        occasion: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch paginated recommendation history for the authenticated user."""
        query = Recommendation.query.filter_by(user_id=user_id)
        if occasion:
            query = query.filter(Recommendation.occasion.ilike(f"%{occasion.strip()}%"))

        paginated = query.order_by(Recommendation.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return {
            "items": [rec.to_dict() for rec in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
            "per_page": paginated.per_page,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev
        }

    @classmethod
    def set_favorite(cls, user_id: int, rec_id: int, is_favorite: bool = True) -> Optional[Dict[str, Any]]:
        """Toggle favorite status for an outfit recommendation."""
        rec = Recommendation.query.filter_by(id=rec_id, user_id=user_id).first()
        if not rec:
            return None

        rec.is_favorite = is_favorite
        db.session.commit()
        return rec.to_dict()

    @classmethod
    def get_favorites(
        cls,
        user_id: int,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """Fetch user's saved favorite outfits."""
        paginated = Recommendation.query.filter_by(
            user_id=user_id,
            is_favorite=True
        ).order_by(Recommendation.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return {
            "items": [rec.to_dict() for rec in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
            "per_page": paginated.per_page,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev
        }

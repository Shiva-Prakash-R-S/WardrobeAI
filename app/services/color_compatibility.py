import math
from typing import Dict, Any, Tuple, Optional, List

# Re-use standard named colors from color_service
from app.services.color_service import NAMED_COLORS, match_closest_color

# Standard fashion neutrals
NEUTRAL_COLORS = {"Black", "White", "Grey", "Beige", "Cream"}
BASE_NEUTRALS = {"Black", "White", "Grey", "Beige", "Cream", "Navy", "Brown"}

# Curated classic fashion color pairings (order-independent)
CURATED_CLASSICS: Dict[frozenset, Tuple[int, str]] = {
    frozenset(["Navy", "Beige"]): (98, "Classic timeless pairing offering sophisticated, warm-cool contrast."),
    frozenset(["Black", "White"]): (100, "High-contrast monochrome icon; crisp, modern, and universally sharp."),
    frozenset(["Grey", "Black"]): (96, "Understated minimalist harmony with sleek architectural depth."),
    frozenset(["White", "Blue"]): (96, "Fresh, breezy contrast reminiscent of coastal and nautical tailoring."),
    frozenset(["Olive", "Beige"]): (95, "Organic earth-tone harmony that feels relaxed and effortlessly refined."),
    frozenset(["Brown", "Cream"]): (96, "Luxurious warm tonal balance with rich equestrian-inspired warmth."),
    frozenset(["Maroon", "Black"]): (95, "Deep, sultry pairing with regal richness and nighttime elegance."),
    frozenset(["Blue", "Grey"]): (94, "Cool urban synergy that balances casual calm with professional polish."),
    frozenset(["Navy", "White"]): (98, "Crisp, maritime-inspired contrast with perennial nautical sophistication."),
    frozenset(["Navy", "Grey"]): (95, "Versatile tailored harmony favored in contemporary sartorial styling."),
    frozenset(["Olive", "Cream"]): (94, "Soft organic palette combining earthy foliage tones with creamy warmth."),
    frozenset(["Brown", "Beige"]): (94, "Subtle tonal warmth echoing heritage suede, linen, and leather textures."),
    frozenset(["Maroon", "Cream"]): (94, "Striking jewel-tone balance; the cream softens the intensity of maroon."),
    frozenset(["Maroon", "White"]): (93, "High-clarity pairing that highlights deep ruby warmth against clean light."),
    frozenset(["Black", "Beige"]): (95, "Modern Parisian-style contrast balancing stark darkness with sand warmth."),
    frozenset(["Grey", "White"]): (94, "Ultra-clean Scandinavian aesthetic that is soft, neutral, and luminous.")
}

# Hue angles (degrees on 360-degree color wheel) for non-neutrals
HUE_ANGLES: Dict[str, float] = {
    "Red": 0.0,
    "Maroon": 345.0,
    "Orange": 30.0,
    "Brown": 25.0,
    "Yellow": 60.0,
    "Olive": 80.0,
    "Green": 120.0,
    "Blue": 210.0,
    "Navy": 225.0,
    "Purple": 280.0,
    "Pink": 330.0,
}


def hex_to_rgb(hex_code: Optional[str]) -> Tuple[int, int, int]:
    """Convert HEX color string to RGB tuple, fallback to Grey if invalid."""
    if not hex_code:
        return 128, 128, 132
    cleaned = hex_code.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join([c * 2 for c in cleaned])
    if len(cleaned) != 6:
        return 128, 128, 132
    try:
        r = int(cleaned[0:2], 16)
        g = int(cleaned[2:4], 16)
        b = int(cleaned[4:6], 16)
        return r, g, b
    except ValueError:
        return 128, 128, 132


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert sRGB (0-255) to CIELAB (L*, a*, b*) using D65 illuminant reference.
    Provides mathematically accurate perceptual lightness and color distances.
    """
    # 1. Normalize sRGB to [0, 1] and linearize (inverse gamma companding)
    def pivot_rgb(c: float) -> float:
        c = c / 255.0
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    lr = pivot_rgb(r) * 100.0
    lg = pivot_rgb(g) * 100.0
    lb = pivot_rgb(b) * 100.0

    # 2. Convert Linear RGB to XYZ (D65 standard)
    x = lr * 0.4124564 + lg * 0.3575761 + lb * 0.1804375
    y = lr * 0.2126729 + lg * 0.7151522 + lb * 0.0721750
    z = lr * 0.0193339 + lg * 0.1191920 + lb * 0.9503041

    # Reference white point D65
    xn, yn, zn = 95.047, 100.000, 108.883
    xr, yr, zr = x / xn, y / yn, z / zn

    # 3. XYZ to CIELAB
    def pivot_lab(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (903.3 * t + 16.0) / 116.0

    fx = pivot_lab(xr)
    fy = pivot_lab(yr)
    fz = pivot_lab(zr)

    l_star = max(0.0, min(100.0, 116.0 * fy - 16.0))
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)

    return round(l_star, 2), round(a_star, 2), round(b_star, 2)


def delta_e_cielab(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """Calculate Euclidean distance in CIELAB perceptual space (CIE76)."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


class ColorCompatibilityService:
    """
    Evaluates color compatibility and styling harmony across garments
    using perceptual CIELAB mathematics, fashion color theory, and curated classics.
    """

    @classmethod
    def resolve_color_name_and_hex(
        cls,
        color_name: Optional[str] = None,
        color_hex: Optional[str] = None
    ) -> Tuple[str, str, Tuple[int, int, int], Tuple[float, float, float]]:
        """
        Normalize color name, hex code, RGB tuple, and CIELAB representation.
        """
        # If color_name matches a standard named color
        if color_name and color_name.capitalize() in NAMED_COLORS:
            canonical_name = color_name.capitalize()
            r, g, b, chex = NAMED_COLORS[canonical_name]
            chosen_hex = color_hex if (color_hex and color_hex.startswith("#")) else chex
            rgb = hex_to_rgb(chosen_hex)
            lab = rgb_to_lab(*rgb)
            return canonical_name, chosen_hex, rgb, lab

        # If color_hex is available, match closest
        if color_hex and color_hex.startswith("#"):
            rgb = hex_to_rgb(color_hex)
            canonical_name, _ = match_closest_color(rgb)
            lab = rgb_to_lab(*rgb)
            return canonical_name, color_hex, rgb, lab

        # Default fallback
        fallback = "Grey"
        r, g, b, chex = NAMED_COLORS[fallback]
        return fallback, chex, (r, g, b), rgb_to_lab(r, g, b)

    @classmethod
    def evaluate_pair(
        cls,
        name1: Optional[str],
        hex1: Optional[str],
        name2: Optional[str],
        hex2: Optional[str]
    ) -> Dict[str, Any]:
        """
        Evaluate compatibility between two clothing items' colors.
        Returns score (0-100), harmony type, and design explanation.
        """
        norm1, hex1_val, rgb1, lab1 = cls.resolve_color_name_and_hex(name1, hex1)
        norm2, hex2_val, rgb2, lab2 = cls.resolve_color_name_and_hex(name2, hex2)

        pair_key = frozenset([norm1, norm2])

        # 1. Curated Classic Harmonies check
        if pair_key in CURATED_CLASSICS:
            score, reason = CURATED_CLASSICS[pair_key]
            return {
                "score": score,
                "harmony_type": "curated_classic",
                "explanation": f"{norm1} + {norm2}: {reason}",
                "color1": norm1,
                "color2": norm2
            }

        # Perceptual properties
        delta_l = abs(lab1[0] - lab2[0])
        delta_e = delta_e_cielab(lab1, lab2)

        # 2. Monochromatic / Tonal check (same canonical hue or very low chroma difference)
        if norm1 == norm2:
            if delta_l > 15:
                # Same family with nice tonal depth (e.g. Light Navy + Deep Navy, Charcoal + Light Grey)
                score = min(96, int(86 + delta_l * 0.2))
                reason = f"Refined monochromatic tonal harmony across {norm1} with natural depth."
                harmony_type = "monochromatic"
            else:
                # Almost identical color
                score = 88
                reason = f"Clean matching {norm1} monochrome statement."
                harmony_type = "monochromatic"
            return {
                "score": score,
                "harmony_type": harmony_type,
                "explanation": reason,
                "color1": norm1,
                "color2": norm2
            }

        # 3. Neutral + Neutral pairing
        if norm1 in BASE_NEUTRALS and norm2 in BASE_NEUTRALS:
            base_score = 92
            if delta_l > 25:
                base_score = 96
            reason = f"Balanced neutral palette combining {norm1} and {norm2} with effortless elegance."
            return {
                "score": base_score,
                "harmony_type": "neutral_harmony",
                "explanation": reason,
                "color1": norm1,
                "color2": norm2
            }

        # 4. Neutral + Accent / Hue pairing
        if norm1 in BASE_NEUTRALS or norm2 in BASE_NEUTRALS:
            neutral = norm1 if norm1 in BASE_NEUTRALS else norm2
            accent = norm2 if norm1 in BASE_NEUTRALS else norm1
            # Neutrals naturally ground any vibrant color
            base_score = 88
            if delta_l > 30:
                base_score += 6
            reason = f"Flattering grounding effect where neutral {neutral} allows {accent} to stand out cleanly."
            return {
                "score": min(95, base_score),
                "harmony_type": "neutral_anchor",
                "explanation": reason,
                "color1": norm1,
                "color2": norm2
            }

        # 5. Hue-based calculations for two chromatic colors
        hue1 = HUE_ANGLES.get(norm1, 0.0)
        hue2 = HUE_ANGLES.get(norm2, 0.0)
        hue_diff = abs(hue1 - hue2)
        if hue_diff > 180.0:
            hue_diff = 360.0 - hue_diff

        # Complementary (angles roughly 150-180 apart)
        if 140.0 <= hue_diff <= 180.0:
            score = 88
            if delta_l > 20:
                score += 5  # Value contrast makes complementary pairings pop tastefully
            return {
                "score": min(94, score),
                "harmony_type": "complementary",
                "explanation": f"Dynamic complementary pairing of {norm1} and {norm2} with bold visual balance.",
                "color1": norm1,
                "color2": norm2
            }

        # Analogous (angles within 30-60 degrees)
        if 20.0 <= hue_diff <= 75.0:
            score = 90
            return {
                "score": score,
                "harmony_type": "analogous",
                "explanation": f"Cohesive analogous harmony of neighboring hues ({norm1} and {norm2}) for a smooth gradient.",
                "color1": norm1,
                "color2": norm2
            }

        # General contrast evaluation
        if delta_l > 40:
            return {
                "score": 85,
                "harmony_type": "contrast",
                "explanation": f"High lightness contrast pairing ({norm1} & {norm2}) that provides crisp distinction.",
                "color1": norm1,
                "color2": norm2
            }

        # Moderate harmony
        return {
            "score": 78,
            "harmony_type": "standard_pair",
            "explanation": f"Gentle pairing of {norm1} and {norm2} suited for casual styling.",
            "color1": norm1,
            "color2": norm2
        }

    @classmethod
    def evaluate_outfit_colors(
        cls,
        top_color: Tuple[Optional[str], Optional[str]],
        bottom_color: Tuple[Optional[str], Optional[str]],
        footwear_color: Optional[Tuple[Optional[str], Optional[str]]] = None,
        accessory_color: Optional[Tuple[Optional[str], Optional[str]]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate complete outfit color palette.
        Weighted combination:
        - Top + Bottom: 50%
        - Bottom + Footwear: 25% (if footwear present)
        - Top + Footwear: 25% (if footwear present)
        - Accessory harmonizing bonus
        """
        tb_eval = cls.evaluate_pair(top_color[0], top_color[1], bottom_color[0], bottom_color[1])
        scores = [tb_eval["score"]]
        weights = [0.50]
        explanations = [tb_eval["explanation"]]

        if footwear_color and (footwear_color[0] or footwear_color[1]):
            tf_eval = cls.evaluate_pair(top_color[0], top_color[1], footwear_color[0], footwear_color[1])
            bf_eval = cls.evaluate_pair(bottom_color[0], bottom_color[1], footwear_color[0], footwear_color[1])
            scores.extend([tf_eval["score"], bf_eval["score"]])
            weights.extend([0.25, 0.25])
            if bf_eval["score"] >= 90:
                explanations.append(f"Footwear ({bf_eval['color2']}) anchors the {bf_eval['color1']} lower silhouette.")

        total_weight = sum(weights)
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        # Accessory bonus check (e.g., neutral accessory or matching shoe/belt)
        accessory_note = None
        if accessory_color and (accessory_color[0] or accessory_color[1]):
            norm_acc, _, _, _ = cls.resolve_color_name_and_hex(accessory_color[0], accessory_color[1])
            if norm_acc in BASE_NEUTRALS:
                weighted_score = min(100.0, weighted_score + 2.0)
                accessory_note = f"Neutral {norm_acc} accessory accents the outfit subtly."
            elif footwear_color:
                norm_foot, _, _, _ = cls.resolve_color_name_and_hex(footwear_color[0], footwear_color[1])
                if norm_acc == norm_foot:
                    weighted_score = min(100.0, weighted_score + 4.0)
                    accessory_note = f"Matching {norm_acc} accessory and footwear create tailored symmetry."

        final_score = int(round(weighted_score))
        combined_explanation = " ".join(explanations)
        if accessory_note:
            combined_explanation += " " + accessory_note

        return {
            "score": max(0, min(100, final_score)),
            "top_bottom": tb_eval,
            "explanation": combined_explanation
        }

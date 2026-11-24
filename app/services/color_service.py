import math
from typing import Dict, Any, Tuple, List
from PIL import Image

# 16 Standard Color definitions as required by the specification
NAMED_COLORS: Dict[str, Tuple[int, int, int, str]] = {
    "Black": (18, 18, 20, "#121214"),
    "White": (245, 245, 248, "#F5F5F8"),
    "Grey": (128, 128, 132, "#808084"),
    "Red": (211, 47, 47, "#D32F2F"),
    "Blue": (25, 118, 210, "#1976D2"),
    "Navy": (15, 32, 67, "#0F2043"),
    "Green": (56, 142, 60, "#388E3C"),
    "Olive": (128, 128, 0, "#808000"),
    "Yellow": (251, 192, 45, "#FBC02D"),
    "Orange": (245, 124, 0, "#F57C00"),
    "Pink": (233, 30, 99, "#E91E63"),
    "Purple": (123, 31, 162, "#7B1FA2"),
    "Brown": (93, 64, 55, "#5D4037"),
    "Beige": (225, 213, 192, "#E1D5C0"),
    "Cream": (255, 253, 208, "#FFFDD0"),
    "Maroon": (128, 0, 32, "#800020"),
}


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Format RGB components as a standard 7-character hexadecimal string."""
    return f"#{r:02X}{g:02X}{b:02X}"


def _color_distance_weighted(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """
    Calculate perceptual weighted Euclidean distance between two RGB colors.
    Human eye is more sensitive to green, then red, then blue.
    """
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    rmean = (r1 + r2) / 2.0
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    return math.sqrt(
        (2 + rmean / 256.0) * (dr ** 2) +
        4.0 * (dg ** 2) +
        (2 + (255 - rmean) / 256.0) * (db ** 2)
    )


def match_closest_color(rgb: Tuple[int, int, int]) -> Tuple[str, str]:
    """
    Find the closest standard color name and canonical HEX code for an RGB color.
    """
    closest_name = "Grey"
    closest_hex = "#808084"
    min_dist = float("inf")

    for name, (cr, cg, cb, chex) in NAMED_COLORS.items():
        dist = _color_distance_weighted(rgb, (cr, cg, cb))
        if dist < min_dist:
            min_dist = dist
            closest_name = name
            closest_hex = chex

    return closest_name, closest_hex


class ColorService:
    @staticmethod
    def detect_dominant_colors(image: Image.Image) -> Dict[str, Any]:
        """
        Analyze an image and extract dominant primary and secondary colors.
        Returns mapped human-readable color names and hex values.
        """
        # Convert to RGB if needed (handling RGBA, CMYK, P, L)
        if image.mode != "RGB":
            # For RGBA, paste onto white background to avoid transparent black artifacts
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                bg = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                bg.paste(image, mask=image.split()[3])
                rgb_img = bg
            else:
                rgb_img = image.convert("RGB")
        else:
            rgb_img = image

        # Resize to 120x120 for fast and reliable processing
        small_img = rgb_img.resize((120, 120), Image.Resampling.BILINEAR)

        # Center crop (sample 80% center area to reduce uniform studio backdrops)
        w, h = small_img.size
        crop_box = (int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9))
        cropped = small_img.crop(crop_box)

        # Quantize to 8 color clusters using Fast Octree
        quantized = cropped.quantize(colors=8, method=Image.Quantize.FASTOCTREE)
        palette = quantized.getpalette()  # Flat list [r0, g0, b0, r1, g1, b1, ...]
        raw_counts = quantized.getcolors()

        if not raw_counts or not palette:
            return {
                "primary_color": "Grey",
                "secondary_color": None,
                "color_hex": "#808084",
                "colors": []
            }

        # Sort clusters by frequency descending
        sorted_clusters = sorted(raw_counts, key=lambda x: x[0], reverse=True)
        total_pixels = sum(count for count, _ in sorted_clusters)

        analyzed_colors: List[Dict[str, Any]] = []
        seen_names = set()

        for count, palette_idx in sorted_clusters:
            idx = palette_idx * 3
            if idx + 2 < len(palette):
                r = palette[idx]
                g = palette[idx + 1]
                b = palette[idx + 2]
                raw_hex = _rgb_to_hex(r, g, b)
                named_color, canon_hex = match_closest_color((r, g, b))
                pct = round((count / total_pixels) * 100, 1)

                if named_color not in seen_names:
                    seen_names.add(named_color)
                    analyzed_colors.append({
                        "name": named_color,
                        "hex": raw_hex,
                        "canonical_hex": canon_hex,
                        "percentage": pct
                    })

        primary = analyzed_colors[0] if len(analyzed_colors) > 0 else {
            "name": "Black", "hex": "#121214", "canonical_hex": "#121214"
        }
        secondary = analyzed_colors[1] if len(analyzed_colors) > 1 else None

        return {
            "primary_color": primary["name"],
            "secondary_color": secondary["name"] if secondary else None,
            "color_hex": primary["hex"],
            "primary_hex": primary["hex"],
            "secondary_hex": secondary["hex"] if secondary else None,
            "detected_palette": analyzed_colors[:4]
        }


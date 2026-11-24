import io
import os
import uuid
from typing import Tuple, Optional
from PIL import Image, ImageOps
from flask import current_app
from werkzeug.datastructures import FileStorage


class ImageValidationError(Exception):
    """Custom exception raised when an image fails format or content verification."""
    pass


class ImageStorageService:
    @staticmethod
    def _get_upload_dir(subdir: str = "clothing") -> str:
        """Ensure upload directory exists and return absolute path."""
        upload_base = current_app.config.get(
            "UPLOAD_FOLDER",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
        )
        target_dir = os.path.join(upload_base, subdir)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    @staticmethod
    def validate_and_open_image(file: FileStorage) -> Image.Image:
        """
        Validate file extension, file size, MIME content, and structural integrity.
        Returns a loaded, orientation-corrected PIL Image in RGB mode.
        """
        if not file or not file.filename:
            raise ImageValidationError("No image file provided.")

        filename = file.filename.lower()
        allowed_exts = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"})
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in allowed_exts:
            raise ImageValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(allowed_exts))}."
            )

        # Read binary data into memory to verify size and content
        file.seek(0)
        data = file.read()
        file.seek(0)

        max_size = current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
        if len(data) > max_size:
            raise ImageValidationError(
                f"Image size exceeds the maximum limit of {max_size // (1024 * 1024)}MB."
            )

        if len(data) == 0:
            raise ImageValidationError("Image file is empty.")

        # Validate image headers and structure with PIL
        try:
            temp_stream = io.BytesIO(data)
            with Image.open(temp_stream) as img:
                img.verify()
        except Exception:
            raise ImageValidationError("Corrupted or invalid image content.")

        # Re-open verified image for processing
        stream = io.BytesIO(data)
        image = Image.open(stream)

        # Correct orientation based on EXIF metadata (camera shots)
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        # Validate dimensions
        w, h = image.size
        if w < 16 or h < 16:
            raise ImageValidationError("Image dimensions are too small (minimum 16x16 pixels).")

        return image

    @classmethod
    def save_clothing_image(cls, file: FileStorage) -> Tuple[str, str, str, str]:
        """
        Processes and stores an uploaded clothing image.
        Generates both optimized full-size image and thumbnail.
        Returns:
            (image_url, thumbnail_url, main_filename, thumb_filename)
        """
        image = cls.validate_and_open_image(file)

        # Ensure RGB mode for standardized JPEG storage
        if image.mode != "RGB":
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                bg = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                bg.paste(image, mask=image.split()[3])
                image = bg
            else:
                image = image.convert("RGB")

        unique_id = uuid.uuid4().hex
        main_filename = f"clothing_{unique_id}.jpg"
        thumb_filename = f"thumb_{unique_id}.jpg"

        clothing_dir = cls._get_upload_dir("clothing")
        thumb_dir = cls._get_upload_dir("thumbnails")

        main_path = os.path.join(clothing_dir, main_filename)
        thumb_path = os.path.join(thumb_dir, thumb_filename)

        # Create main image (scaled down if exceeds MAX_IMAGE_DIMENSION)
        max_dim = current_app.config.get("MAX_IMAGE_DIMENSION", 1600)
        main_copy = image.copy()
        if max(main_copy.size) > max_dim:
            main_copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        main_copy.save(main_path, format="JPEG", quality=85, optimize=True)

        # Create thumbnail (fit to 300x300)
        thumb_dim = current_app.config.get("THUMBNAIL_DIMENSION", (300, 300))
        thumb_copy = image.copy()
        thumb_copy.thumbnail(thumb_dim, Image.Resampling.LANCZOS)
        thumb_copy.save(thumb_path, format="JPEG", quality=80, optimize=True)

        image_url = f"/api/clothing/images/{main_filename}"
        thumbnail_url = f"/api/clothing/images/{thumb_filename}"

        return image_url, thumbnail_url, main_filename, thumb_filename

    @classmethod
    def delete_clothing_images(cls, image_url: Optional[str], thumbnail_url: Optional[str]) -> None:
        """
        Safely delete stored image files from disk.
        Prevents directory traversal by sanitizing with os.path.basename.
        """
        clothing_dir = cls._get_upload_dir("clothing")
        thumb_dir = cls._get_upload_dir("thumbnails")

        if image_url:
            filename = os.path.basename(image_url)
            file_path = os.path.join(clothing_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        if thumbnail_url:
            thumb_name = os.path.basename(thumbnail_url)
            thumb_path = os.path.join(thumb_dir, thumb_name)
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                except OSError:
                    pass

    @classmethod
    def get_image_file_path(cls, filename: str) -> Optional[str]:
        """
        Resolve safe local filesystem path for a requested filename.
        Returns None if file does not exist or path traversal is attempted.
        """
        safe_name = os.path.basename(filename)
        if safe_name.startswith("thumb_"):
            target_dir = cls._get_upload_dir("thumbnails")
        else:
            target_dir = cls._get_upload_dir("clothing")

        full_path = os.path.join(target_dir, safe_name)
        if os.path.isfile(full_path):
            return full_path
        return None

    @classmethod
    def save_body_image(cls, file: FileStorage) -> Tuple[str, str, str, str]:
        """
        Processes and stores an uploaded user body photograph.
        Generates both optimized full-size portrait and thumbnail.
        Returns:
            (image_url, thumbnail_url, main_filename, thumb_filename)
        """
        image = cls.validate_and_open_image(file)

        if image.mode != "RGB":
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                bg = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                bg.paste(image, mask=image.split()[3])
                image = bg
            else:
                image = image.convert("RGB")

        unique_id = uuid.uuid4().hex
        main_filename = f"body_{unique_id}.jpg"
        thumb_filename = f"thumb_body_{unique_id}.jpg"

        body_dir = cls._get_upload_dir("body_profiles")
        thumb_dir = cls._get_upload_dir("thumbnails")

        main_path = os.path.join(body_dir, main_filename)
        thumb_path = os.path.join(thumb_dir, thumb_filename)

        # Scale down if exceeds MAX_IMAGE_DIMENSION while keeping aspect ratio
        max_dim = current_app.config.get("MAX_IMAGE_DIMENSION", 1600)
        main_copy = image.copy()
        if max(main_copy.size) > max_dim:
            main_copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        main_copy.save(main_path, format="JPEG", quality=88, optimize=True)

        # Thumbnail (300x300 fit)
        thumb_dim = current_app.config.get("THUMBNAIL_DIMENSION", (300, 300))
        thumb_copy = image.copy()
        thumb_copy.thumbnail(thumb_dim, Image.Resampling.LANCZOS)
        thumb_copy.save(thumb_path, format="JPEG", quality=80, optimize=True)

        image_url = f"/api/body-profile/images/{main_filename}"
        thumbnail_url = f"/api/body-profile/images/{thumb_filename}"

        return image_url, thumbnail_url, main_filename, thumb_filename

    @classmethod
    def delete_body_images(cls, image_url: Optional[str], thumbnail_url: Optional[str]) -> None:
        """Safely delete body profile images from disk."""
        body_dir = cls._get_upload_dir("body_profiles")
        thumb_dir = cls._get_upload_dir("thumbnails")

        if image_url:
            filename = os.path.basename(image_url)
            file_path = os.path.join(body_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        if thumbnail_url:
            thumb_name = os.path.basename(thumbnail_url)
            thumb_path = os.path.join(thumb_dir, thumb_name)
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                except OSError:
                    pass

    @classmethod
    def get_body_image_path(cls, filename: str) -> Optional[str]:
        """Resolve safe filesystem path for a body profile image."""
        safe_name = os.path.basename(filename)
        if safe_name.startswith("thumb_"):
            target_dir = cls._get_upload_dir("thumbnails")
        else:
            target_dir = cls._get_upload_dir("body_profiles")

        full_path = os.path.join(target_dir, safe_name)
        if os.path.isfile(full_path):
            return full_path
        return None

    @classmethod
    def save_tryon_result_image(cls, image: Image.Image) -> Tuple[str, str, str]:
        """
        Saves a generated virtual try-on composite/diffusion image.
        Returns (image_url, main_filename, full_path).
        """
        if image.mode != "RGB":
            image = image.convert("RGB")

        unique_id = uuid.uuid4().hex
        main_filename = f"tryon_{unique_id}.jpg"
        target_dir = cls._get_upload_dir("tryon_results")
        full_path = os.path.join(target_dir, main_filename)

        image.save(full_path, format="JPEG", quality=90, optimize=True)
        image_url = f"/api/tryon/images/{main_filename}"
        return image_url, main_filename, full_path

    @classmethod
    def delete_tryon_result_image(cls, image_url: Optional[str]) -> None:
        """Safely remove a try-on result image from disk."""
        if image_url:
            target_dir = cls._get_upload_dir("tryon_results")
            safe_name = os.path.basename(image_url)
            full_path = os.path.join(target_dir, safe_name)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass

    @classmethod
    def get_tryon_image_path(cls, filename: str) -> Optional[str]:
        """Resolve safe filesystem path for a tryon result image."""
        safe_name = os.path.basename(filename)
        target_dir = cls._get_upload_dir("tryon_results")
        full_path = os.path.join(target_dir, safe_name)
        if os.path.isfile(full_path):
            return full_path
        return None



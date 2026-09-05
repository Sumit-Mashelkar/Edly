import io
from pathlib import Path
from typing import Any, Optional, Tuple

from PIL import Image

REFERENCE_PATH = Path(__file__).resolve().parents[3] / "seed" / "reference.json"


def load_reference() -> dict[str, Any]:
    import json

    with REFERENCE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_artwork_upload(file_bytes: bytes, filename: str, artwork_type: str) -> Tuple[bool, Optional[str]]:
    reference = load_reference()
    specs = reference["artwork_specs"].get(artwork_type)
    if specs is None:
        return False, f"Unsupported artwork type '{artwork_type}'. Use poster, banner, or thumbnail."

    if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return False, "Upload a PNG, JPG, or WEBP image file."

    try:
        image = Image.open(io.BytesIO(file_bytes))
        width, height = image.size
    except Exception:
        return False, "The uploaded file is not a valid image. Please upload a real image file."

    max_kb = int(specs["max_kb"])
    if len(file_bytes) > max_kb * 1024:
        return False, f"The {artwork_type} image is too large. Keep it under {max_kb} KB."

    expected_aspect = specs["aspect"]
    if expected_aspect == "2:3":
        ratio_ok = width / height == 2 / 3
    elif expected_aspect == "16:9":
        ratio_ok = abs((width / height) - (16 / 9)) < 0.02
    else:
        ratio_ok = True

    if not ratio_ok:
        return False, (
            f"The {artwork_type} image must use {expected_aspect} aspect ratio. "
            f"Use approximately {specs['target_px'][0]}x{specs['target_px'][1]} pixels."
        )

    target_width, target_height = specs["target_px"]
    if width < target_width or height < target_height:
        return False, (
            f"The {artwork_type} image is too small. Please use at least {target_width}x{target_height} pixels "
            f"for a {artwork_type} file."
        )

    return True, None

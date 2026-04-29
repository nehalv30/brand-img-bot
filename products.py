import json
import random
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from config import DATA_FILE, PROD_DIR, ALLOWED_EXTENSIONS


def load_products() -> list[dict]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data or not isinstance(data, list):
        raise ValueError("products.json must be a non-empty list")
    return data


def _collect_images(folder: Path) -> list[Path]:
    """Return all valid image files in folder (non-recursive)."""
    if not folder.exists():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix.lower() in ALLOWED_EXTENSIONS
    )


def _type_fallback_folders(product_folder: str) -> list[Path]:
    """
    If the exact product folder is empty, return broader type-level folders
    so we still have a reference image while per-product photos are being added.

    Priority order:
      1. Exact product folder      (e.g. assets/KSH/Silver/)
      2. Parent type folder        (e.g. assets/KSH/)
      3. General products folder   (assets/products/)
    """
    exact = PROD_DIR / product_folder
    parts = product_folder.split("/")
    parent = PROD_DIR / parts[0] if len(parts) > 1 else None
    general = PROD_DIR / "products"

    folders = [exact]
    if parent:
        folders.append(parent)
    folders.append(general)
    return folders


def _load_image(path: Path) -> Image.Image | None:
    try:
        img = Image.open(path)
        img.load()
        return img
    except (UnidentifiedImageError, OSError):
        return None


def get_reference_image(product: dict, rng: random.Random) -> tuple[Path, Image.Image] | None:
    """
    Return (path, PIL Image) for a product reference photo.

    Tries the product-specific folder first, then falls back to the
    type-level folder, then the general products/ pool.
    Returns None only if no usable image exists anywhere.
    """
    for folder in _type_fallback_folders(product["folder"]):
        paths = _collect_images(folder)
        if not paths:
            continue
        rng.shuffle(paths)
        for path in paths:
            img = _load_image(path)
            if img is not None:
                return path, img
    return None

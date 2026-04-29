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


def get_image_paths(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix.lower() in ALLOWED_EXTENSIONS
    )


def get_reference_image(product: dict, rng: random.Random) -> tuple[Path, Image.Image] | None:
    """Pick a random product photo and return (path, PIL Image), or None if unavailable."""
    folder = PROD_DIR / product["folder"]
    paths = get_image_paths(folder)
    if not paths:
        return None
    rng.shuffle(paths)
    for path in paths:
        try:
            img = Image.open(path)
            img.load()
            return path, img
        except UnidentifiedImageError:
            continue
    return None

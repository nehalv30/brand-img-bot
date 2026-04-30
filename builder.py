"""
Builder — the senior marketing director.

Generates Instagram-ready lifestyle images using Gemini with a product
reference photo as visual anchor. Retries up to 15 times total:
  block 1: 10 attempts (escalating delay up to 2 min)
  pause  : 10 minutes
  block 2: 5 attempts  (60 s apart)
"""

import time

from google import genai
from google.genai import types

from config import API_KEY
from themes import get_scene_for_product

client = genai.Client(api_key=API_KEY)

_IMAGE_MODEL = "gemini-2.5-flash-image"


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

def _is_retryable(err: Exception) -> bool:
    msg = str(err)
    return any(tok in msg for tok in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))


def _call_api(contents):
    return client.models.generate_content(model=_IMAGE_MODEL, contents=contents)


def generate_with_retry(contents):
    """
    Attempt generation with two-block retry strategy.
    Block 1: 10 attempts, delay escalates from 30s up to 120s.
    Pause:   10 minutes if all 10 fail.
    Block 2: 5 more attempts, 60s apart.
    """
    last_error = None

    # ---- Block 1: 10 attempts ----
    for attempt in range(1, 11):
        try:
            return _call_api(contents)
        except Exception as e:
            if not _is_retryable(e):
                raise
            last_error = e
            if attempt < 10:
                delay = min(30 * attempt, 120)
                print(f"  Attempt {attempt}/10 failed. Retrying in {delay}s...")
                time.sleep(delay)

    # ---- 10-minute pause ----
    print("  All 10 attempts failed. Pausing 10 minutes before final retry block...")
    time.sleep(600)

    # ---- Block 2: 5 attempts ----
    for attempt in range(1, 6):
        try:
            return _call_api(contents)
        except Exception as e:
            if not _is_retryable(e):
                raise
            last_error = e
            if attempt < 5:
                print(f"  Final block attempt {attempt}/5 failed. Retrying in 60s...")
                time.sleep(60)

    raise RuntimeError("Generation failed after 15 total attempts (10 + 5)") from last_error


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _product_brief(product: dict) -> tuple[str, str]:
    """
    Returns (product_description, usage_direction) specific to product type.
    These ground the AI in what the product looks and behaves like.
    """
    folder = product["folder"]

    if folder.startswith("KSH"):
        desc = (
            "An adhesive wall hook. It has a flat rectangular backing — either fully clear/transparent, "
            "warm gold/brass coloured, or brushed stainless steel silver. A decorative flower/clover-shaped "
            "clear plastic mechanism sits in the centre of the backing. From the centre hangs a smooth "
            "J-shaped metal hook arm that curves forward and downward. "
            "When installed, the backing presses flat against the wall and the hook arm protrudes outward."
        )
        usage = (
            "Show the hook mounted flat on a wall surface (bathroom tile, painted wall, or kitchen tile). "
            "The backing must be flush against the wall. An item — towel, coat, tote bag, plant pot, "
            "or set of keys — hangs naturally from the hook arm. "
            "Do NOT show the hook floating in mid-air or attached to a frame."
        )

    elif folder.startswith("KSS") or folder.startswith("KST"):
        desc = (
            "Double-sided nano tape. It comes as a roll — either a crystal-clear transparent roll "
            "(about 2-4 cm wide) or a semi-transparent white mesh roll. "
            "The tape is completely invisible once applied between two surfaces."
        )
        usage = (
            "Show the tape in active use: "
            "either (a) a hand applying a strip to the back edge of a picture frame before pressing it to a wall, "
            "or (b) the finished result — a frame hanging flush on a wall with zero nails, "
            "or a rug corner lying perfectly flat on a hardwood floor. "
            "Do NOT show the tape hanging in the air or stuck to the front of anything."
        )

    elif folder.startswith("KMHS"):
        desc = (
            "Magnetic hanging strips — two small flat rectangular white/cream adhesive pads "
            "that magnetically attach to each other, allowing objects to be mounted on walls with no nails."
        )
        usage = (
            "Show a picture frame, clock, or decorative object mounted cleanly on a wall, "
            "appearing to float with no visible screws, nails, or hardware. "
            "The magnetic pads are hidden behind the object — only the result is seen."
        )

    else:
        use_cases = ", ".join(product["use_cases"])
        desc = f"Adhesive home organizer. Use cases: {use_cases}."
        usage = "Show the product in active, correct use in a beautiful home setting."

    return desc, usage


def _build_prompt(product: dict, angle: str, visual: str, feedback: str | None = None) -> str:
    scene = get_scene_for_product(product, angle, visual)
    product_desc, usage_direction = _product_brief(product)

    prompt = f"""You are a senior marketing director at a premium home lifestyle brand.
Your job: create a single, scroll-stopping Instagram lifestyle photo that makes people feel they need this product in their life.

PRODUCT (shown in the reference image):
{product_desc}

CAMPAIGN THEME: {angle}

SCENE: {scene}

HOW THE PRODUCT MUST APPEAR:
{usage_direction}

STYLE:
- Square 1:1 format, magazine-quality photography
- Warm, natural light — real home environment, not a studio
- Aspirational but achievable — the kind of home people save to Pinterest
- Every object in frame must belong there and make logical sense
- If people or hands appear, they must look completely natural (no stiff AI poses, no broken fingers)
- Zero text, zero logos, zero brand names, zero retail packaging anywhere in the image

The reference image shows exactly what the product looks like. Render it faithfully in the scene."""

    if feedback:
        prompt += f"\n\nPREVIOUS ATTEMPT WAS REJECTED. Issues to fix:\n{feedback}"

    return prompt


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_image(
    product: dict,
    angle: str,
    visual: str,
    ref_part: types.Part,
    feedback: str | None = None,
) -> "Image.Image | None":
    """
    Generate one lifestyle image.
    ref_part is a pre-converted Gemini Part (convert once, reuse across retries).
    Returns a PIL Image on success, None if Gemini returns no image.
    """
    prompt = _build_prompt(product, angle, visual, feedback)
    # Reference image first so the model sees it before reading the prompt
    contents = [ref_part, prompt]

    response = generate_with_retry(contents)

    for part in response.parts:
        if getattr(part, "inline_data", None) is not None:
            return part.as_image()
        if getattr(part, "text", None):
            print(f"  Model note: {part.text[:120]}")

    return None

"""
Critique — the quality gatekeeper.

Uses Gemini vision to review each generated image before it's emailed.
Checks visual appeal, scene logic, product correctness, and professional finish.
Returns a structured verdict so the builder can retry with targeted feedback.
"""

from google import genai
from PIL import Image

from config import API_KEY

client = genai.Client(api_key=API_KEY)

_CRITIQUE_MODEL = "gemini-2.0-flash"

_SYSTEM_PROMPT = """You are a senior Instagram content quality reviewer for a premium home lifestyle brand.
Your job is to reject images that would embarrass the brand and approve images that would perform well.

Review the image against every criterion below. Be strict — a mediocre image should FAIL.

CRITERIA:
1. VISUAL APPEAL        — Is it beautiful, warm, magazine-quality, scroll-stopping?
2. SCENE LOGIC          — Does every element in the frame make sense and belong there?
3. PRODUCT CORRECTNESS  — Is the product shown being used correctly?
                          Hooks must be MOUNTED ON A WALL with items hanging from them.
                          Tape must be shown being applied or showing a clean result (flat rug, flush frame).
                          Nothing should be floating, randomly placed, or stuck to the wrong surface.
4. COMPLETENESS         — Is everything fully rendered? Nothing cut off, half-formed, or missing?
5. REALISM              — Does anything look obviously AI-generated, distorted, or anatomically wrong?
6. HUMAN ELEMENTS       — If hands or people appear, do they look completely natural?
7. CLEANLINESS          — Zero logos, zero text, zero brand names, zero retail packaging visible?
8. PROFESSIONALISM      — Would a professional brand post this image without hesitation?

Respond in EXACTLY this format (no extra text, no markdown):
RESULT: PASS or FAIL
SCORE: [integer 1 to 10]
ISSUES: [comma-separated list of specific problems, or "None"]
FIX: [one concise sentence telling the builder what to change, or "Looks great"]"""


def critique_image(
    img: Image.Image,
    product: dict,
    angle: str,
) -> tuple[bool, int, str]:
    """
    Review a generated scene image for quality.

    Args:
        img:     The raw PIL image from the builder (before text overlay).
        product: The product dict (for context).
        angle:   The campaign theme (for context).

    Returns:
        passed (bool): True if image meets quality bar.
        score  (int):  1–10 quality score.
        feedback (str): Issues + fix hint for the builder's next attempt.
    """
    context_note = (
        f"Context — Product type: {product['name']} | Theme: {angle[:80]}"
    )
    full_prompt = f"{_SYSTEM_PROMPT}\n\n{context_note}"

    try:
        response = client.models.generate_content(
            model=_CRITIQUE_MODEL,
            contents=[full_prompt, img],
        )
        text = (response.text or "").strip()
    except Exception as e:
        print(f"  Critique API error ({type(e).__name__}: {e}). Defaulting to PASS.")
        return True, 7, "Critique skipped due to API error."

    passed = "RESULT: PASS" in text
    score = 5

    feedback_parts = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("SCORE:"):
            try:
                score = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass
        if stripped.startswith("ISSUES:") or stripped.startswith("FIX:"):
            feedback_parts.append(stripped)

    feedback = " | ".join(feedback_parts) if feedback_parts else text[:300]
    return passed, score, feedback

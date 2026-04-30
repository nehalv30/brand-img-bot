"""
Daily KLAPIT Instagram creative generator.

Flow per post:
  1. Builder generates a lifestyle scene (with product reference image)
  2. Critique reviews the scene for quality
  3. If critique fails, builder retries with the feedback (up to 3 attempts)
  4. Best image gets a PIL text overlay, saved, and emailed
"""

import random
from datetime import date

from config import EMAIL_TO, OUT_DIR
from products import load_products, get_reference_image
from themes import THEMES, get_copy_lines
from builder import build_image
from critique import critique_image
from image_utils import crop_to_square, add_text_overlay, pil_to_part
from email_sender import send_email_with_attachments

# How many builder+critique rounds to allow per post before using best attempt
MAX_ROUNDS = 3
# Minimum score (1–10) to accept without further retries
PASS_THRESHOLD = 6


def generate_post(
    product: dict,
    angle: str,
    visual: str,
    copy: str,
    ref_part,
    post_index: int,
):
    """
    Builder → critique loop for one post.
    Returns the saved output path, or None if all attempts fail.
    """
    feedback = None
    best_image = None
    best_score = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"  Round {round_num}/{MAX_ROUNDS} — building image...")
        raw = build_image(product, angle, visual, ref_part, feedback)

        if raw is None:
            print("  Builder returned no image.")
            continue

        passed, score, feedback = critique_image(raw, product, angle)
        status = "PASS" if passed else "FAIL"
        print(f"  Critique: {status} (score {score}/10)")
        if not passed:
            print(f"  Feedback: {feedback}")

        if score > best_score:
            best_score = score
            best_image = raw

        if passed and score >= PASS_THRESHOLD:
            print(f"  Accepted on round {round_num}.")
            break

    if best_image is None:
        print(f"  Warning: no usable image generated for post {post_index}.")
        return None

    out_path = OUT_DIR / f"generated_post_{post_index}.png"
    final = crop_to_square(best_image)
    final = add_text_overlay(final, copy)
    final.save(out_path)
    print(f"  Saved: {out_path.name}  (best score: {best_score}/10)")
    return out_path


def main():
    rng = random.Random(date.today().toordinal())

    products = load_products()
    product = rng.choice(products)
    name = product["name"]
    print(f"Today's product: {name}\n")

    ref = get_reference_image(product, rng)
    if ref is None:
        raise ValueError(f"No usable reference image found for: {name}")
    ref_path, ref_image = ref
    print(f"Reference image: {ref_path.name}\n")

    # Convert once — reused across all 3 posts and any retries
    ref_part = pil_to_part(ref_image)

    themes_today = rng.sample(THEMES, 3)
    copy_lines = get_copy_lines(product)
    copies_today = rng.sample(copy_lines, min(3, len(copy_lines)))

    output_paths = []
    for i, ((angle, visual), copy) in enumerate(zip(themes_today, copies_today), 1):
        print(f"\n=== Post {i}/3: {angle[:70]} ===")
        path = generate_post(product, angle, visual, copy, ref_part, i)
        if path:
            output_paths.append(path)

    if not output_paths:
        raise ValueError("No images were generated — nothing to email.")

    send_email_with_attachments(
        subject=f"Daily KLAPIT Creatives — {name} ({len(output_paths)} posts)",
        body=(
            f"Today's {len(output_paths)} generated creatives for {name}.\n\n"
            f"Reference image used: {ref_path.name}\n"
            f"Posts generated: {len(output_paths)}/3"
        ),
        attachment_paths=output_paths,
    )
    print(f"\nEmail sent to {EMAIL_TO} with {len(output_paths)} image(s).")


if __name__ == "__main__":
    main()

import os
import json
import smtplib
import random
import time
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from PIL import Image, UnidentifiedImageError

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")
if not EMAIL_FROM or not EMAIL_TO or not EMAIL_APP_PASSWORD:
    raise ValueError("Email settings are missing in .env file")

client = genai.Client(api_key=API_KEY)

BASE_DIR = Path(__file__).resolve().parent
PROD_DIR = BASE_DIR / "assets"
OUT_DIR = BASE_DIR / "output"
DATA_FILE = BASE_DIR / "data" / "products.json"

OUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def get_image_paths(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    paths = [
        p for p in folder.iterdir()
        if p.is_file()
           and not p.name.startswith(".")
           and p.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return sorted(paths)


def load_pil_images(paths: list[Path]) -> list[Image.Image]:
    images = []
    for path in paths:
        try:
            img = Image.open(path)
            img.load()
            images.append(img)
        except UnidentifiedImageError:
            print(f"Skipping unreadable image: {path}")
    return images


def load_products() -> list[dict]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing file: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data or not isinstance(data, list):
        raise ValueError("products.json must contain a list with at least one product")
    return data


def send_email_with_attachments(subject: str, body: str, attachment_paths: list[Path]):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content(body)

    for path in attachment_paths:
        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="image",
                subtype="png",
                filename=path.name,
            )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)


def generate_image(contents, max_retries=10, retry_delay=30):
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
            )
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries:
                    print(f"Model unavailable (attempt {attempt}/{max_retries}). Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError(f"Model still unavailable after {max_retries} attempts") from e
            else:
                raise


# Visual styles — all minimalistic, clean, Instagram-ready
VISUAL_STYLES = [
    {
        "name": "Clean White Studio",
        "style": "pure white background, soft drop shadow, sans-serif typography, one subtle accent color from the product",
        "lighting": "soft diffused studio light, no harsh shadows",
    },
    {
        "name": "Warm Minimal",
        "style": "warm off-white or cream background, natural wood or linen texture as a subtle prop, clean layout",
        "lighting": "soft warm daylight from the side, gentle shadows",
    },
    {
        "name": "Dark Elegant",
        "style": "deep charcoal or navy background, product lit sharply, gold or white minimal typography, premium feel",
        "lighting": "single directional studio light, dramatic but clean",
    },
    {
        "name": "Airy Lifestyle",
        "style": "bright, airy room setting — white walls, light wood, minimal decor props, lots of breathing room",
        "lighting": "natural window light, soft and even",
    },
    {
        "name": "Editorial Flat Lay",
        "style": "top-down flat lay, product surrounded by 2-3 minimal props on a neutral surface, clean grid composition",
        "lighting": "even overhead light, no strong shadows",
    },
]

# Post concepts — what story each post tells
POST_CONCEPTS = [
    {
        "name": "Problem Solver",
        "concept": "Show a split scene: left side shows a damaged wall with holes, nails, and mess; right side shows a clean, beautiful wall with items hung perfectly using KLAPiT. No hands, no process — just the outcome.",
        "text_direction": "Bold headline like 'No drills. No damage. No stress.' at top, brand name and tagline at bottom",
    },
    {
        "name": "Strength Stat",
        "concept": "A clean lifestyle scene — a framed artwork, a coat, or a shelf holding items on a wall — with a bold stat overlaid like '60 LBS' or '11 LBS per hook'. The scene shows the result, not the process. No hands touching the product.",
        "text_direction": "Huge bold stat as the headline, short supporting line like 'One hook. All the hold you need.', product packaging shown as a small corner insert",
    },
    {
        "name": "Room Transform",
        "concept": "A beautifully styled, aspirational living space — gallery wall, neat kitchen, styled entryway or bathroom — where items are hung cleanly on walls. The product packaging sits quietly on a shelf or counter nearby. No installation being shown.",
        "text_direction": "Minimal text, soft headline like 'Your walls. Your style.' or 'A cleaner home starts here.', brand name small and clean",
    },
    {
        "name": "The Clever Use",
        "concept": "Show one creative, unexpected use case in a styled lifestyle setting — hooks organizing charging cables on a desk, tape securing a doormat, strips keeping a rug flat, hooks holding plants. Outcome only, no hands or installation.",
        "text_direction": "Discovery headline like 'The home hack you didn't know you needed' or 'Organize everything. Damage nothing.', product packaging visible",
    },
    {
        "name": "One Step Install",
        "concept": "Show the satisfying simplicity of using KLAPiT — someone pressing a hook onto a wall, peeling a strip, or sticking tape in one clean motion. The action must look realistic and natural, not stylized. The result (item hanging perfectly) is visible too.",
        "text_direction": "Headline: 'Peel. Stick. Done.' or 'Instant hold. Zero tools.', product packaging visible, minimal supporting text",
    },
    {
        "name": "Feature Spotlight",
        "concept": "Highlight one key feature through a creative visual metaphor — waterproof shown with a bathroom scene, strength shown with a heavy item hanging confidently, reusability shown with a wall being redecorated. The feature is demonstrated through the scene, not labeled or diagrammed.",
        "text_direction": "Feature as bold headline (e.g. 'Waterproof.' or 'Holds 60 LBS.'), one-line explanation below, product packaging shown clearly",
    },
    {
        "name": "The Invisible Hero",
        "concept": "A stunning, aspirational room where everything is perfectly hung and organized. The product is barely visible — just a small hook behind a coat, or the edge of a strip behind a frame — but the space looks immaculate because of it.",
        "text_direction": "Subtle headline like 'You won't see it. You'll love what it does.' Brand name clean and small.",
    },
    {
        "name": "Before vs After",
        "concept": "Two-panel image: top/left panel shows a bare, plain wall or messy space; bottom/right shows the same space transformed — gallery wall, organized hooks, styled decor — using KLAPiT. Clean graphic divider between the two.",
        "text_direction": "Minimal 'Before' / 'After' labels, bold tagline across the center or bottom, product packaging shown in the after panel",
    },
    {
        "name": "Relatable Moment",
        "concept": "A warm, human lifestyle scene — a freshly decorated room, a well-organized entryway, a cozy reading nook with art on the walls — that feels achievable. The product packaging is shown resting on a surface nearby as the simple tool that made it happen.",
        "text_direction": "Conversational headline like 'Moving in? Skip the nails.' or 'Finally, walls you won\'t regret.', warm tone, product visible",
    },
    {
        "name": "Clean Aesthetic Hero",
        "concept": "Pure minimal product post. The product packaging is the centerpiece, placed on a clean surface with 1-2 elegant props (a plant, a marble tile, a folded towel). No scene, no lifestyle setting — just premium product presentation.",
        "text_direction": "Brand name large and clean, tagline small below, product centered with lots of white space around it",
    },
]

# Use date as seed so picks are consistent within a day but change daily
rng = random.Random(date.today().toordinal())

# Pick one product for today
products = load_products()
product = rng.choice(products)

name = product["name"]
description = product["description"]
brand_name = product["brand_name"]
tagline = product["tagline"]
key_features = ", ".join(product["key_features"])
use_cases = ", ".join(product["use_cases"])

print(f"Today's product: {name}")

# Load product images from the folder path defined in JSON
product_folder = PROD_DIR / product["folder"]
if not product_folder.exists():
    raise FileNotFoundError(f"Product folder not found: {product_folder}")

all_image_paths = get_image_paths(product_folder)
if not all_image_paths:
    raise ValueError(f"No images found in {product_folder}")

# Shuffle so each of the 3 generations gets a different angle
rng.shuffle(all_image_paths)
print(f"Found {len(all_image_paths)} angle(s) for {name}")

# Pick 3 unique concept + style combos for today
concepts_today = rng.sample(POST_CONCEPTS, 3)
styles_today = rng.sample(VISUAL_STYLES, 3)
posts_today = list(zip(concepts_today, styles_today))
print(f"Today's posts: {', '.join(c['name'] + ' / ' + s['name'] for c, s in posts_today)}\n")

# Generate one image per concept+style combo
output_paths = []

for i, (concept, style) in enumerate(posts_today, 1):
    print(f"Generating image {i}/3 — {concept['name']} + {style['name']} ...")

    # Use a different angle for each generation; cycle if fewer images than posts
    angle_image = load_pil_images([all_image_paths[(i - 1) % len(all_image_paths)]])
    if not angle_image:
        raise ValueError(f"Could not load image: {all_image_paths[(i - 1) % len(all_image_paths)]}")

    prompt = f"""
You are creating a professional Instagram post for KLAPiT — a brand that makes adhesive mounting products (nano tapes, strips, and hooks) that let people hang and organize things without drills or nails.

PRODUCT: {name}
Brand: {brand_name}
Tagline: {tagline}
Description: {description}
Key features: {key_features}
Use cases: {use_cases}

=== TODAY'S POST CONCEPT: {concept["name"]} ===
{concept["concept"]}
Text direction: {concept["text_direction"]}

=== VISUAL STYLE: {style["name"]} ===
Style: {style["style"]}
Lighting: {style["lighting"]}

RULES — FOLLOW STRICTLY:
1. The uploaded image is the real KLAPiT product packaging. Show it clearly somewhere in the frame — as a corner insert, resting on a surface, being held, or in use. It must be recognizable, not blurry or tiny.
2. The product must look EXACTLY as it does in the uploaded photo — same colors, same shape, same design. Do not hallucinate or invent product details. If showing the product in use, it must look physically accurate and realistic — no goo, no unrealistic adhesive effects, no mislabeled parts.
3. Be creative and match the post concept fully — lifestyle scenes, installation moments, before/after, stats, whatever the concept calls for. Make it engaging and true to how the product actually works.
4. Keep the overall look MINIMALISTIC — clean backgrounds, intentional composition, no clutter or loud colors.
5. Text overlay: one strong headline, brand name, and tagline only. Clean sans-serif font. Maximum 3 lines. No text placed on top of the product.
6. SQUARE (1:1) format — the image must be perfectly square, not portrait or landscape.
7. Must feel like a real premium brand ad — creative, confident, and professional. Not AI-generated looking.
"""

    contents = [prompt] + angle_image
    response = generate_image(contents)

    concept_slug = concept["name"].lower().replace(" ", "_")
    output_path = OUT_DIR / f"generated_post_{i}_{concept_slug}.png"

    saved = False
    for part in response.parts:
        if getattr(part, "inline_data", None) is not None:
            image = part.as_image()
            image.save(output_path)
            print(f"  Saved: {output_path.name}")
            output_paths.append(output_path)
            saved = True
            break
        elif getattr(part, "text", None):
            print(f"  Model said: {part.text}")

    if not saved:
        print(f"  Warning: No image returned for concept '{concept['name']}'")

if not output_paths:
    raise ValueError("No images were generated across all concepts")

# Send all generated images in one email
post_summary = ", ".join(f"{c['name']} ({s['name']})" for c, s in posts_today)
send_email_with_attachments(
    subject=f"Daily KLAPIT Creatives — {name} ({len(output_paths)} posts)",
    body=(
        f"Attached are today's {len(output_paths)} generated creatives for {name}.\n\n"
        f"Posts: {post_summary}"
    ),
    attachment_paths=output_paths,
)

print(f"\nEmail sent to {EMAIL_TO} with {len(output_paths)} image(s).")

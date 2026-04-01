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


# Visual styles — varied moods, all clean and Instagram-ready
VISUAL_STYLES = [
    {
        "name": "Bright & Airy",
        "style": "bright white or off-white background, lots of natural light, clean and fresh feel, light wood or marble accents, minimal props",
        "lighting": "soft natural daylight, even and bright, no harsh shadows",
        "people": False,
    },
    {
        "name": "Warm Home",
        "style": "warm cream or beige tones, cozy home setting, natural textures like linen, wood, or stone, lived-in but styled",
        "lighting": "warm golden side light, soft shadows",
        "people": False,
    },
    {
        "name": "Dark & Premium",
        "style": "deep charcoal or slate background, high contrast, gold or white typography, editorial and premium feel",
        "lighting": "single directional spotlight, dramatic but controlled",
        "people": False,
    },
    {
        "name": "Real Person Lifestyle",
        "style": "a real person (hands or full body) naturally interacting with the product or enjoying the result — hanging something, organizing their space, or simply living in a well-organized home",
        "lighting": "natural indoor light, realistic and warm",
        "people": True,
    },
    {
        "name": "Clean Studio",
        "style": "pure white background, product as hero, soft shadow, absolutely minimal — like a premium product catalogue",
        "lighting": "soft studio light from above, gentle and even",
        "people": False,
    },
    {
        "name": "Lifestyle Scene",
        "style": "a beautifully styled real room — bathroom, entryway, kitchen, or living room — product shown in context, aspirational but achievable",
        "lighting": "natural window light, warm and realistic",
        "people": False,
    },
]

# Post concepts — what story each post tells
POST_CONCEPTS = [
    {
        "name": "Problem Solver",
        "concept": "Show the contrast between the old painful way (drills, nails, wall damage, mess) and the clean KLAPiT solution. Could be a split image or a single scene that implies the solution. Make the viewer think 'why didn't I know about this sooner?'",
        "text": "Bold headline like 'No drills. No damage. No stress.' or 'There's a smarter way to hang things.'",
    },
    {
        "name": "Strength Stat",
        "concept": "Lead with a powerful number — the holding strength of the product. Show something impressively heavy hanging confidently on a wall (a coat, backpack, framed mirror, plant). The stat is the headline, the scene proves it.",
        "text": "Huge bold stat (e.g. '11 LBS', '60 LBS', '500 LBS') as headline, supporting line like 'One strip. Serious hold.'",
    },
    {
        "name": "Room Transform",
        "concept": "An aspirational, beautifully organized space — gallery wall, styled bathroom, neat entryway — that looks achievable. The product made this possible. Could include a person admiring or enjoying the space.",
        "text": "Soft headline like 'Your walls. Your style.' or 'This is what no-drill hanging looks like.'",
    },
    {
        "name": "The Clever Use",
        "concept": "Show one specific, creative, relatable use case that surprises or delights — hooks holding a hanging plant, tape securing a doormat, strips organizing cables, magnetic strips holding remotes. Make it feel like a discovery.",
        "text": "Headline like 'Hang your plants. Not your worries.' or 'The hack your home needs.' — specific to the use case shown",
    },
    {
        "name": "In Action",
        "concept": "Show a person using the product naturally — pressing a hook onto a tile wall, hanging a frame, sticking tape to secure a rug edge. The moment should feel real and satisfying, not staged. Show the product clearly and the result visible in the same frame.",
        "text": "Action headline like 'Peel. Stick. Done.' or 'Instant hold. Zero tools.' — short and punchy",
    },
    {
        "name": "Feature Hero",
        "concept": "Pick one standout feature of this specific product and build the entire visual around it. Waterproof = bathroom with water splashing nearby. Residue-free = a clean wall after removing a hook. Reusable = someone repositioning a frame effortlessly.",
        "text": "Feature as the headline (e.g. 'Waterproof.' / 'Zero residue.' / 'Reuse it.'), one short explanation line below",
    },
    {
        "name": "Before vs After",
        "concept": "A clean two-panel split: before shows a cluttered, bare, or nail-damaged wall; after shows the same wall beautifully organized using KLAPiT. Both panels should look photographic and real, not illustrated.",
        "text": "Clean 'Before' / 'After' labels, bold tagline at the bottom like 'PEEL. STICK. HANG. DONE.'",
    },
    {
        "name": "Relatable Moment",
        "concept": "A warm, human scene that feels instantly relatable — someone moving into a new apartment, a parent organizing kids' room, a person finally tackling that bare wall. The product is the simple, satisfying answer.",
        "text": "Conversational headline like 'Moving in? Skip the nails.' or 'Finally, a wall you're proud of.' — warm and human",
    },
    {
        "name": "Clean Product Hero",
        "concept": "The product packaging is the star — centered, well-lit, styled with 2-3 minimal lifestyle props that match its use case (a folded towel, a small plant, a marble surface). Clean and premium like a luxury brand.",
        "text": "Brand name as the headline, tagline below — minimal and confident",
    },
    {
        "name": "Social Proof Feel",
        "concept": "A warm, authentic-looking scene that feels like something a happy customer would post — a beautifully hung gallery wall, an organized bathroom, a cozy entryway. Genuine and aspirational at the same time.",
        "text": "Headline like 'This is why we don't drill anymore.' or 'Every home needs this.' — conversational and real",
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

    people_note = "Include a real person naturally in this scene — hands, partial body, or full lifestyle moment." if style.get("people") else "No people needed — let the product and scene tell the story."

    prompt = f"""
You are a world-class creative director creating a premium Instagram post for KLAPiT — a home organization brand making nano-adhesive hooks, tapes, and strips that let people hang and organize anything without drills or nails. Think 3M Command Strips but more modern and premium.

PRODUCT BEING FEATURED: {name}
Brand: {brand_name}
Tagline: {tagline}
What it does: {description}
Key features: {key_features}
Best used for: {use_cases}

━━━ POST CONCEPT: {concept["name"]} ━━━
{concept["concept"]}
Text to use: {concept["text"]}

━━━ VISUAL STYLE: {style["name"]} ━━━
{style["style"]}
Lighting: {style["lighting"]}
{people_note}

━━━ PRODUCT IMAGE INSTRUCTIONS ━━━
The uploaded photo IS the real KLAPiT product packaging. You must:
- Reproduce it with 100% visual accuracy — exact same colors, shape, logo, and design
- Show it clearly and fully in the frame — NEVER crop, blur, or shrink it to the point it becomes unreadable
- Place it naturally: on a counter, shelf, corner of the image, or being held — wherever fits the concept
- The product is the HERO — it should be immediately noticeable when someone sees the post

━━━ SCENE & COMPOSITION ━━━
- Choose a scene that directly matches what this product is used for:
  Hooks → towels, coats, bags, plants, keys hanging on a wall
  Tape/Strips → frames hung on wall, rugs secured, kitchen items mounted
- Make the scene feel like a real home, not a generic stock photo
- Every prop and element must make sense for this product's use case
- Cohesive color palette — background, props, text, and product should all feel designed together

━━━ TYPOGRAPHY ━━━
- Place the text intentionally — top, bottom, or overlaid on a clean area
- Use bold, clean sans-serif for headlines. Max 3 lines total.
- Text color must contrast clearly with the background

━━━ NON-NEGOTIABLE FORMAT RULES ━━━
- Output must be a PERFECT SQUARE (1:1 ratio) — not portrait, not landscape, exactly square
- Minimalistic and premium — clean beats busy every time
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

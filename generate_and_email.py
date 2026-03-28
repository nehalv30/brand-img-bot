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
REF_DIR = BASE_DIR / "assets" / "brand_refs"
PROD_DIR = BASE_DIR / "assets" / "products"
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


THEMES = [
    {
        "name": "Minimalist Zen",
        "style": "ultra-clean white space, single hero product shot, subtle shadow, sans-serif typography, monochromatic palette with one accent color",
        "mood": "calm, premium, uncluttered",
        "lighting": "soft diffused studio light with gentle highlights",
        "composition": "centered product floating on white, with minimal text and lots of breathing room",
    },
    {
        "name": "Futuristic Tech",
        "style": "dark background with glowing neon outlines, holographic reflections, geometric grid lines, futuristic HUD elements",
        "mood": "innovative, cutting-edge, high-tech",
        "lighting": "dramatic back-lit glow with cyan/purple neon accents",
        "composition": "product at an angle with light trails and digital data particles surrounding it",
    },
    {
        "name": "Lifestyle Warmth",
        "style": "warm earthy tones, natural textures (wood, linen, stone), cozy home setting, soft bokeh background",
        "mood": "homey, relatable, aspirational everyday life",
        "lighting": "warm golden-hour window light, soft shadows",
        "composition": "product placed in a real home scene with complementary lifestyle props",
    },
    {
        "name": "Bold Pop Art",
        "style": "vivid saturated colors, halftone dot patterns, thick outlines, retro-modern comic aesthetic, strong typography",
        "mood": "energetic, fun, eye-catching",
        "lighting": "flat graphic look with strong shadows and highlights, no photorealism",
        "composition": "product enlarged as the hero with graphic shapes, starbursts, and bold tagline text",
    },
    {
        "name": "Nature & Sustainability",
        "style": "lush greenery, botanical elements, organic shapes, earthy green/brown/cream palette, eco-conscious feel",
        "mood": "fresh, natural, responsible, trustworthy",
        "lighting": "bright natural daylight with dappled leaf shadows",
        "composition": "product nestled among plants and natural materials, grounded and organic framing",
    },
    {
        "name": "Luxury Editorial",
        "style": "black and gold palette, marble or velvet textures, serif typography, high-fashion magazine layout",
        "mood": "exclusive, sophisticated, aspirational",
        "lighting": "dramatic side-lit Rembrandt lighting on a dark background",
        "composition": "product as the centerpiece with elegant negative space, metallic accents, and refined details",
    },
    {
        "name": "Urban Street",
        "style": "gritty concrete textures, graffiti-inspired typography, raw industrial environment, bold contrasting colors",
        "mood": "authentic, edgy, urban-cool",
        "lighting": "harsh directional street light with strong shadows",
        "composition": "product mounted on or placed against an urban wall with dynamic angles and street-art elements",
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

# Load one random variation image from the product's folder
product_folder = PROD_DIR / name
if not product_folder.exists():
    raise FileNotFoundError(
        f"Product folder not found: {product_folder}\n"
        f"Expected: assets/products/{name}/"
    )

variation_paths = get_image_paths(product_folder)
if not variation_paths:
    raise ValueError(f"No images found in {product_folder}")

selected_variation = rng.choice(variation_paths)
print(f"Selected variation: {selected_variation.name}")

product_images = load_pil_images([selected_variation])
if not product_images:
    raise ValueError(f"Could not load image: {selected_variation}")

# Load brand reference images (limit to 2)
ref_paths = get_image_paths(REF_DIR)
if not ref_paths:
    raise ValueError("No reference images found in assets/brand_refs")
ref_images = load_pil_images(ref_paths[:2])

# Pick 3 unique themes for today
themes_today = rng.sample(THEMES, 3)
print(f"Today's themes: {', '.join(t['name'] for t in themes_today)}\n")

# Generate one image per theme
output_paths = []

for i, theme in enumerate(themes_today, 1):
    print(f"Generating image {i}/3 — Theme: {theme['name']} ...")

    prompt = f"""
Create a stunning Instagram-style product advertisement image.

Brand: {brand_name}
Product: {name}
Tagline: {tagline}
Description: {description}
Key features: {key_features}
Use cases: {use_cases}

=== TODAY'S CREATIVE THEME: {theme["name"]} ===

Visual style: {theme["style"]}
Mood and feel: {theme["mood"]}
Lighting direction: {theme["lighting"]}
Composition guide: {theme["composition"]}

Use the uploaded reference images only for brand color and logo placement guidance.
Use the uploaded product image as the actual product to feature — show it clearly and prominently.

Requirements:
- The product packaging must be clearly visible and recognizable
- The tagline "{tagline}" should appear as styled text in the image
- The brand name "{brand_name}" should be subtly but clearly present
- Apply the theme above faithfully — this must look and feel like "{theme["name"]}"
- Do NOT copy the reference images; create an entirely fresh original composition
- Optimize for square (1:1) Instagram format
- Make it thumb-stopping and scroll-stopping on social media
"""

    contents = [prompt] + ref_images + product_images
    response = generate_image(contents)

    theme_slug = theme["name"].lower().replace(" ", "_").replace("&", "and")
    output_path = OUT_DIR / f"generated_post_{i}_{theme_slug}.png"

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
        print(f"  Warning: No image returned for theme '{theme['name']}'")

if not output_paths:
    raise ValueError("No images were generated across all themes")

# Send all generated images in one email
theme_names = ", ".join(t["name"] for t in themes_today)
send_email_with_attachments(
    subject=f"Daily KLAPIT Creatives — {name} ({len(output_paths)} looks)",
    body=(
        f"Attached are today's {len(output_paths)} generated creatives for {name}.\n\n"
        f"Themes: {theme_names}\n\n"
        f"Variation used: {selected_variation.name}"
    ),
    attachment_paths=output_paths,
)

print(f"\nEmail sent to {EMAIL_TO} with {len(output_paths)} image(s).")

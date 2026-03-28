import os
import json
import smtplib
import random
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


def load_product_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing file: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data or not isinstance(data, list):
        raise ValueError("products.json must contain a list with at least one product")

    return data[0]


def send_email_with_attachment(subject: str, body: str, attachment_path: Path):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content(body)

    with open(attachment_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="image",
            subtype="png",
            filename=attachment_path.name
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)


product = load_product_data()

ref_paths = get_image_paths(REF_DIR)
product_paths = get_image_paths(PROD_DIR)

if not ref_paths:
    raise ValueError("No reference images found in assets/brand_refs")
if not product_paths:
    raise ValueError("No product images found in assets/products")

ref_images = load_pil_images(ref_paths)
product_images = load_pil_images(product_paths)

if not ref_images:
    raise ValueError("No valid reference images could be opened")
if not product_images:
    raise ValueError("No valid product images could be opened")

name = product["name"]
description = product["description"]
brand_name = product["brand_name"]
tagline = product["tagline"]
key_features = ", ".join(product["key_features"])
use_cases = ", ".join(product["use_cases"])

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

# Use date as seed so the theme is consistent within a day but changes daily
rng = random.Random(date.today().toordinal())
theme = rng.choice(THEMES)

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

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=contents,
)

saved = False
output_path = OUT_DIR / "generated_post.png"

for part in response.parts:
    if getattr(part, "inline_data", None) is not None:
        image = part.as_image()
        image.save(output_path)
        print(f"Image saved to: {output_path}")
        saved = True
        break
    elif getattr(part, "text", None):
        print(part.text)

if not saved:
    raise ValueError("No image was returned by Gemini")

send_email_with_attachment(
    subject=f"Daily KLAPIT Creative - {name} [{theme['name']}]",
    body=f"Attached is today's generated creative for {name}.\n\nTheme: {theme['name']}\n{theme['mood'].capitalize()}.",
    attachment_path=output_path
)

print(f"Email sent to: {EMAIL_TO}")

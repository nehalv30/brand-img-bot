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
EMAIL_CC = "marketing@kosmosmith.com"
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
    msg["Cc"] = EMAIL_CC
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


# Visual styles — each has a distinct color palette and mood
VISUAL_STYLES = [
    {
        "name": "Crisp White & Natural Wood",
        "palette": "pure white walls, warm light oak wood accents, soft cream textiles",
        "lighting": "bright diffused natural daylight from a large window, even and shadow-free",
        "people": False,
    },
    {
        "name": "Warm Terracotta & Cream",
        "palette": "terracotta and burnt orange tones, cream plaster walls, natural linen and rattan props",
        "lighting": "warm amber side light, soft organic shadows that feel golden and inviting",
        "people": False,
    },
    {
        "name": "Deep Sage & Off-White",
        "palette": "deep sage green walls or background, off-white and warm beige accents, brass or matte black hardware",
        "lighting": "soft directional natural light from the side, gentle shadows, calm and premium",
        "people": False,
    },
    {
        "name": "Moody Dark & Gold",
        "palette": "deep charcoal or dark slate walls, gold and warm white accents, high contrast and editorial",
        "lighting": "single strong directional spotlight, dramatic controlled shadows",
        "people": False,
    },
    {
        "name": "Scandinavian Minimal",
        "palette": "white and light grey, pale birch wood, single muted accent color (dusty blue or blush pink)",
        "lighting": "cool soft daylight, clean and almost clinical but warm — like a Stockholm apartment",
        "people": False,
    },
    {
        "name": "Warm Candid Person",
        "palette": "warm neutrals — cream, sand, warm white — lived-in but beautiful, cozy and real",
        "lighting": "warm natural indoor light, soft shadows, feels like a real human moment",
        "people": True,
    },
    {
        "name": "Bold Color Pop",
        "palette": "one saturated background color — cobalt blue, forest green, or deep blush — product and props in white or neutral to pop against it",
        "lighting": "flat even light, graphic and clean, like a modern brand poster",
        "people": False,
    },
    {
        "name": "Golden Hour Warm",
        "palette": "honey, amber, and warm gold tones throughout — feels like late afternoon sun in a beautiful home",
        "lighting": "warm directional golden hour light from the side, long soft shadows",
        "people": False,
    },
    {
        "name": "Modern Minimal Black & White",
        "palette": "pure black and white only — stark, graphic, editorial. One element in a single accent color for impact.",
        "lighting": "high contrast studio light — crisp shadows, bold and confident",
        "people": False,
    },
    {
        "name": "Soft Blush & Marble",
        "palette": "soft blush pink, white marble textures, brushed gold or rose gold accents — elegant and feminine",
        "lighting": "soft even light, almost glowing, feels luxurious and aspirational",
        "people": False,
    },
]

# Post concepts — relatable human moments and varied content formats
POST_CONCEPTS = [
    {
        "name": "Moving Day Relief",
        "concept": "That specific relief of moving into a new place and realising you can decorate without drilling. Show a person or a styled new apartment space being set up beautifully — art going up, hooks being placed — with zero mess and zero tools.",
        "text": "'Moving in? Leave the drill behind.' or 'New home. Zero holes. All vibes.' — warm, relatable, relief-filled.",
    },
    {
        "name": "The 5-Minute Win",
        "concept": "Show the satisfying result of a quick, easy win — a space that went from bare to beautiful in minutes. No tools, no mess, no contractor. Just a product, two hands, and a beautiful result. Make the viewer feel like they can do this TODAY.",
        "text": "'5 minutes. Zero tools. This.' or 'That corner you've been ignoring? Fixed.' — punchy and motivating.",
    },
    {
        "name": "Landlord Won't Know",
        "concept": "Playful take on the renter experience — decorating freely without fear of losing your deposit. The visual should feel like a small victory. A beautifully styled wall or organized space, completely damage-free.",
        "text": "Witty, playful copy: 'Your landlord will never know.' or 'Full deposit. Full decor.' — light and fun.",
    },
    {
        "name": "Strength That Surprises",
        "concept": "Lead with the jaw-dropping weight capacity of this product. Show something heavier than you'd expect hanging perfectly confidently. The stat is the headline, the scene is the proof.",
        "text": "Giant bold weight number from the product features (e.g. '60 LBS' or '500 LBS'). One sharp line below: 'No nails. No kidding.' — powerful and direct.",
    },
    {
        "name": "The ASMR Close-Up",
        "concept": "An extreme close-up, satisfying detail shot — the product being pressed firmly into place, a strip being smoothed, a hook clicking flat against tile. ASMR-worthy. No wide scene needed. Pure satisfying detail that stops the scroll.",
        "text": "Minimal text — one short line placed in a corner: 'Clean hold. Every time.' or 'Pressed. Locked. Done.' — quiet and confident.",
    },
    {
        "name": "Before It Was Bare",
        "concept": "A clean two-panel split — LEFT: a sad, bare, undecorated wall or messy corner. RIGHT: the exact same space, transformed and beautiful. The product is the only thing that changed. Make both panels look photographic and real.",
        "text": "Simple 'Before' and 'After' labels on each panel. One bold line at the bottom: 'PEEL. PRESS. PERFECT.' — satisfying and final.",
    },
    {
        "name": "The Invisible Hero",
        "concept": "The product doing its job so cleanly it's almost invisible. A beautifully mounted frame, a floating plant, a perfectly secured rug — and if you look closely, the product is there, quietly doing the work. Elegance through simplicity.",
        "text": "Subtle copy: 'The best products disappear.' or 'Strong enough to hold. Clean enough to hide.' — clever and premium.",
    },
    {
        "name": "That One Corner",
        "concept": "Everyone has that one corner, wall, or spot in their home they've been meaning to fix. Show it solved — beautifully organized, hooks in place, frames hung, clutter gone. Make the viewer think 'I need to do that to my space right now.'",
        "text": "'That corner you've been ignoring deserves better.' or 'Every wall has potential.' — relatable and inspiring.",
    },
    {
        "name": "Morning Routine Ready",
        "concept": "Show the product as part of a beautiful morning routine — coat and bag hanging ready by the door, keys on a hook, an organized space that makes your morning feel calm. Aspirational but achievable daily life.",
        "text": "'Your mornings, but better.' or 'Grab and go. Every single day.' — calm, lifestyle-oriented.",
    },
    {
        "name": "The Bold Poster",
        "concept": "Typography dominates the image — one giant, punchy headline in massive bold letters takes up most of the frame. The product is shown small but clearly. Feels like a modern campaign billboard. No fluff, just impact.",
        "text": "3–5 word all-caps headline: 'NO NAILS. NO LIMITS.' or 'HANG ANYTHING. DAMAGE NOTHING.' or 'YOUR WALLS. YOUR RULES.' — bold, loud, confident.",
    },
    {
        "name": "One Feature, Full Commitment",
        "concept": "Pick ONE standout feature of this product and make the whole image about it. Waterproof = steamy bathroom scene. Residue-free = pristine clean wall after a hook is removed. Reusable = hands effortlessly repositioning a frame. One idea. No distractions.",
        "text": "One or two word feature headline — 'Waterproof.' / 'Zero residue.' / 'Reusable.' — then one clean supporting line below.",
    },
    {
        "name": "Dream Home Moment",
        "concept": "Pure aspirational home decor — a specific beautifully styled room corner that makes the viewer stop and save the post. The product is part of what makes it possible, doing its job naturally. Feels like a home magazine spread.",
        "text": "'This is what your walls have been waiting for.' or 'Home goals. No drill required.' — warm and aspirational.",
    },
    {
        "name": "The Smart Swap",
        "concept": "Show the contrast between old-school (drill, nails, wall damage, tools) and this product's clean solution. Not a messy infographic — a beautiful visual contrast. Two worlds: messy/damaged vs. clean/effortless. The smart choice is obvious.",
        "text": "'Nails vs this. Easy choice.' or 'Same wall. Smarter solution.' — confident, slightly witty.",
    },
    {
        "name": "Plant Parent Goals",
        "concept": "Show hanging plants elevated to an art form — trailing pothos, small succulents, air plants — hung using the product. Green, lush, and alive against a beautiful wall. Speaks to the huge plant-loving home decor audience.",
        "text": "'Hang your plants. Not your worries.' or 'Green walls. Zero holes.' — light, fun, relatable to plant lovers.",
    },
    {
        "name": "The Organized Life",
        "concept": "Show a beautifully organized functional space — entryway with hooks for coats and bags, bathroom with hooks for towels, kitchen with mounted spice holders. Real utility made beautiful. The kind of organization that makes life feel calmer.",
        "text": "'Less clutter. More calm.' or 'Everything in its place.' — peaceful, aspirational, deeply relatable.",
    },
]

def get_product_scenes(product: dict) -> list[str]:
    folder = product["folder"]
    if folder.startswith("KMHS"):
        return [
            "A gallery wall of 3 perfectly level frames on a clean white wall. In the corner of one frame, a slim magnetic strip is just barely visible — the only mounting hardware. Close-up angle, clean and precise.",
            "Hands effortlessly sliding a framed picture sideways to reposition it on the wall. The magnetic strip allows smooth, damage-free adjustment. Capture the satisfying moment of easy repositioning.",
            "A minimalist home office: a small whiteboard or clipboard magnetically mounted flat to the side of a monitor stand. Practical, sleek, no screws or tape.",
            "A styled living room feature wall: 4 frames arranged in a gallery layout, all perfectly level. Magnetic strips visible as slim, intentional design details at the corners.",
            "A close-up of two magnetic pads connecting — one on the wall, one on the back of a frame — snapping together cleanly. Satisfying and technical.",
        ]
    elif folder.startswith("KSS") or folder.startswith("KST"):
        return [
            "Hands pressing a transparent nano-tape strip firmly along the back edge of a picture frame, smoothing it flat — close-up, satisfying, clean.",
            "A framed print mounted flush to a white wall. At one corner, a transparent strip catches the light — the only mounting hardware visible. Minimal and damage-free.",
            "Close-up of a clear tape strip being slowly peeled from its liner, the nano-texture glistening in soft light. Feels technical and premium.",
            "A rental apartment living room: a full gallery wall of art mounted entirely with tape. A small inset detail shows zero nail holes on the wall. Bold headline opportunity.",
            "A jute rug corner lying perfectly flat on light hardwood floor. A slim transparent strip runs along the underside edge — no curling, no tripping hazard.",
            "A bathroom shelf mounted cleanly to white subway tile — no drill holes, no grout cracking. The tape strip at each mounting corner is clean and confident.",
        ]
    elif folder.startswith("KSH"):
        return [
            "A spa-like bathroom: a thick white towel draped over a sleek chrome hook mounted on white tile. Minimal, clean, luxurious.",
            "A styled apartment entryway: three evenly spaced hooks on a wall — a coat on one, a leather bag on the second, keys on the third. Organised, beautiful, real.",
            "A clear hook on a white wall with a small trailing pothos plant hanging from it. The hook is nearly invisible — the plant appears to float. Minimal and magical.",
            "A kitchen cabinet side panel: linen aprons and oven mitts hanging from two hooks. Practical but styled — warm tones, natural textures.",
            "A minimalist bedroom wall: a matte gold hook holds a woven bag and a straw hat. Warm, aesthetic, intentional — feels like a boutique hotel.",
        ]
    else:
        use_cases = product["use_cases"]
        return [f"A beautifully styled home scene showing {u.lower()} — clean, aspirational, minimal." for u in use_cases[:5]]


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

# Load product image as visual reference for the AI
product_folder = PROD_DIR / product["folder"]
if not product_folder.exists():
    raise FileNotFoundError(f"Product folder not found: {product_folder}")
all_image_paths = get_image_paths(product_folder)
if not all_image_paths:
    raise ValueError(f"No images found in {product_folder}")

# Pick 3 unique concept + style combos and scenes for today
concepts_today = rng.sample(POST_CONCEPTS, 3)
styles_today = rng.sample(VISUAL_STYLES, 3)
scenes_today = rng.sample(get_product_scenes(product), 3)
posts_today = list(zip(concepts_today, styles_today, scenes_today))
print(f"Today's posts: {', '.join(c['name'] + ' / ' + s['name'] for c, s, _ in posts_today)}\n")

# Generate one image per concept+style+scene combo
output_paths = []

for i, (concept, style, scene) in enumerate(posts_today, 1):
    print(f"Generating image {i}/3 — {concept['name']} + {style['name']} ...")

    ref_image = load_pil_images([all_image_paths[(i - 1) % len(all_image_paths)]])
    if not ref_image:
        raise ValueError(f"Could not load reference image")

    people_note = "Include a real person naturally in this scene — hands using the product, partial body in a candid home moment. Authentic, not stock-photo staged." if style.get("people") else "No people. Let the product and scene speak."

    prompt = f"""
You are a senior art director at a world-class Instagram marketing agency. Create one premium, scroll-stopping square Instagram post for a home organization brand that makes nano-adhesive hooks, tapes, and strips — products that let people hang and organize anything without drilling or damaging walls.

Audience: renters, home decor lovers, minimalists aged 25–40 who care deeply about how their home looks.

━━━ REFERENCE IMAGE ━━━
The uploaded image shows the actual physical product. Study it carefully:
- Note the exact shape, color, size, and material of the actual hook / tape strip / magnetic pad
- You will show this exact physical product (not the retail box, not the packaging) being used naturally in the scene
- Reproduce its real appearance accurately — same color, same shape, same proportions
- Do NOT show the retail box, cardboard backing, or any packaging
- Do NOT show any brand name or logo anywhere in the image

━━━ THE SCENE TO CREATE ━━━
{scene}

Execute this scene with full creative commitment. Beautiful, magazine-quality. Do not substitute a different scene.

━━━ COLOR PALETTE & MOOD ━━━
{style["name"]}: {style["palette"]}
Lighting: {style["lighting"]}
{people_note}
Make the colors feel intentional and eye-catching — the kind of image people stop scrolling for and save.

━━━ COPY / TEXT IN THE IMAGE ━━━
Theme: {concept["name"]}
Write copy in this style: {concept["text"]}

Typography rules:
- Every word spelled perfectly — proofread letter by letter before rendering
- Bold clean sans-serif (Helvetica / Futura style)
- Max 3 lines, placed in top or bottom third of image
- High contrast — instantly readable at a glance
- NO brand names, NO logos, NO product names in the text

━━━ NON-NEGOTIABLE ━━━
- PERFECT SQUARE: 1:1 ratio — not portrait, not landscape
- Physical product visible and accurate to the reference image
- No retail packaging or box anywhere in the image
- No brand name or logo anywhere in the image
- Premium, eye-catching, intentional — every pixel earns its place
"""

    contents = [prompt] + ref_image

    contents = [prompt]
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
post_summary = ", ".join(f"{c['name']} ({s['name']})" for c, s, _ in posts_today)
send_email_with_attachments(
    subject=f"Daily KLAPIT Creatives — {name} ({len(output_paths)} posts)",
    body=(
        f"Attached are today's {len(output_paths)} generated creatives for {name}.\n\n"
        f"Posts: {post_summary}"
    ),
    attachment_paths=output_paths,
)

print(f"\nEmail sent to {EMAIL_TO} with {len(output_paths)} image(s).")

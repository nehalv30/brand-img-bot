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


# Creative angles — emotional moments and human stories (not scene descriptions)
CREATIVE_ANGLES = [
    "the relief of getting your full rental deposit back",
    "moving into your very first apartment with bare walls",
    "that corner you walk past every day and silently cringe at",
    "the 5-minute weekend project that changes everything",
    "coming home after a long day to a calm, organized space",
    "showing your newly decorated home to friends for the first time",
    "the quiet satisfaction of everything finally being in its place",
    "the anxiety of renting from a strict landlord",
    "the 'I wish I'd known about this sooner' moment",
    "a home that looks like it belongs in a design magazine",
    "the before photo you're too embarrassed to show anyone",
    "Sunday morning rituals in a beautifully organized space",
    "the 'no tools, no problem' generation of home decorators",
    "strength that surprises you — holding more than you'd ever expect",
    "the invisible solution to a very visible problem",
    "the organized parent who somehow has it all together",
    "a minimalist who refuses to compromise on style",
    "seasonal refresh — new year, new home, zero damage",
    "the entryway that sets the mood the moment you walk in",
    "a bathroom that feels like checking into a boutique hotel",
    "the home office that finally makes you want to work",
    "the kitchen that makes cooking feel like a ritual",
    "the bedroom wall that went from bare to beautiful overnight",
    "a plant lover creating a living wall without touching the plaster",
    "the joy of rearranging your home on a whim, no consequences",
    "a gallery wall that took 20 minutes and cost nothing to repair",
    "the flex of a perfectly organized space that took zero effort to maintain",
    "a child's room that can be redecorated every few months",
    "the friend everyone calls when they move — because they have the hack",
    "discovering you don't need a contractor for any of this",
    "what good design actually looks like when you get close up",
    "a home so organized it feels like a life upgrade",
    "the satisfying click and hold of something done right",
    "renting without sacrificing your personal style — finally",
    "the detail that makes guests ask 'how did you do that?'",
    "a fresh start in a new space — making it yours without fear",
]

# Visual moods — emotional atmosphere, not just aesthetics
VISUAL_MOODS = [
    "warm golden afternoon light, honey tones, feels like home",
    "crisp bright morning light, white walls, clean fresh start",
    "moody and dramatic — dark walls, strong contrast, editorial",
    "soft and dreamy — blush, marble, gold, luxurious and calm",
    "bold graphic color — one strong background color, product pops",
    "Scandinavian calm — pale wood, white, minimal, serene",
    "warm earthy — terracotta, linen, rattan, real and lived-in",
    "sharp editorial — high contrast, fashion magazine energy",
    "cozy human warmth — real home, soft shadows, authentic",
    "deep sage green walls, warm brass, quietly premium",
    "midnight blue and white — striking, confident, premium",
    "sun-drenched and airy — bleached wood, cotton, holiday feeling",
]

# Copy lines per product type — punchy, varied, no brand names
COPY_BY_TYPE = {
    "KMHS": [
        "NO NAILS.\nPERFECTLY LEVEL.", "SNAP. HANG. DONE.", "REPOSITION ANYTIME.\nZERO DAMAGE.",
        "GALLERY WALL.\nZERO HOLES.", "YOUR DEPOSIT IS SAFE.", "YOUR WALLS. YOUR RULES.",
        "SMALL PRODUCT.\nBIG DIFFERENCE.", "BEFORE / AFTER.\nPEEL. PRESS. PERFECT.",
        "DAMAGE FREE.\nEVERY TIME.", "THE SMARTER WAY TO HANG.",
    ],
    "KSS": [
        "HOLDS 60 LBS.\nLEAVES NOTHING BEHIND.", "NO NAILS. NO MARKS. NO WORRIES.",
        "FLAT FLOORS. SAFE SPACES.", "DRILLS ARE OVERRATED.", "NANO TECHNOLOGY. REAL HOLD.",
        "YOUR WHOLE GALLERY.\nZERO HOLES.", "THERE'S A SMARTER WAY.", "MOUNT ANYTHING.\nDAMAGE NOTHING.",
        "CLEAR. STRONG. INVISIBLE.", "PEEL. PRESS. DONE.",
    ],
    "KST": [
        "HOLDS 500 LBS.\nLEAVES NOTHING BEHIND.", "NO NAILS. NO MARKS. NO WORRIES.",
        "FLAT FLOORS. SAFE SPACES.", "DRILLS ARE OVERRATED.", "NANO TECHNOLOGY. REAL HOLD.",
        "YOUR WHOLE GALLERY.\nZERO HOLES.", "THERE'S A SMARTER WAY.", "MOUNT ANYTHING.\nDAMAGE NOTHING.",
        "TOUGH HOLD. CLEAN REMOVAL.", "ONE STRIP. SERIOUS HOLD.",
    ],
    "KSH": [
        "DAMAGE-FREE. EVERY DAY.", "YOUR HOME. ORGANIZED.", "HANG YOUR PLANTS.\nNOT YOUR WORRIES.",
        "MORNING ROUTINE. SORTED.", "SMALL HOOK. BIG STYLE.", "ORGANIZED. DAMAGE FREE.",
        "YOUR BATHROOM.\nFINALLY ORGANIZED.", "BEFORE / AFTER.\nTHE ONLY CHANGE YOU NEED.",
        "STICK IT. HANG IT. LOVE IT.", "ZERO HOLES. ALL STYLE.",
    ],
    "DEFAULT": [
        "HANG ANYTHING.\nDAMAGE NOTHING.", "NO DRILLS. NO DAMAGE. NO STRESS.",
        "YOUR WALLS.\nYOUR STYLE.", "PEEL. PRESS. PERFECT.",
        "THE SMARTER WAY TO HANG.", "ZERO HOLES. FULL STYLE.",
    ],
}

def get_copy_lines(product: dict) -> list[str]:
    folder = product["folder"]
    for key in COPY_BY_TYPE:
        if folder.startswith(key):
            return COPY_BY_TYPE[key]
    return COPY_BY_TYPE["DEFAULT"]


def get_product_type_context(product: dict) -> str:
    folder = product["folder"]
    if folder.startswith("KMHS"):
        return "magnetic hanging strips — two small magnetic pads that attach to the wall and the back of an object, holding it firmly with no screws or nails. The pads are slim, flat, and nearly invisible once in place."
    elif folder.startswith("KSS") or folder.startswith("KST"):
        return "double-sided nano-tape — a clear transparent strip that sticks between two surfaces and holds them together invisibly. The tape itself is never visible from the front; only the result (a mounted frame, secured rug, or attached shelf) is seen."
    elif folder.startswith("KSH"):
        return "adhesive wall hooks — small sleek hooks that press flat onto any wall surface. The hook body is visible on the wall; items hang from it naturally. No drilling, no screws, completely removable."
    return "nano-adhesive home organization product that lets people hang and organize without drilling"


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

# Pick 3 unique creative combinations for today
angles_today = rng.sample(CREATIVE_ANGLES, 3)
moods_today = rng.sample(VISUAL_MOODS, 3)
copy_lines = get_copy_lines(product)
copies_today = rng.sample(copy_lines, min(3, len(copy_lines)))
product_type = get_product_type_context(product)

print(f"Today's angles: {', '.join(angles_today)}\n")

# Generate one image per combination
output_paths = []

for i, (angle, mood, copy) in enumerate(zip(angles_today, moods_today, copies_today), 1):
    print(f"Generating image {i}/3 — angle: '{angle}' ...")

    ref_image = load_pil_images([all_image_paths[(i - 1) % len(all_image_paths)]])
    if not ref_image:
        raise ValueError("Could not load reference image")

    visual_description = product.get("visual_description", product_type)

    prompt = f"""Create a premium Instagram square photo (1:1 ratio) for a home organization product.

PRODUCT: {name}
WHAT IT LOOKS LIKE (match this exactly): {visual_description}
USE CASES: {use_cases}

The uploaded image shows the real product — study it carefully and reproduce the physical product's exact appearance, color, shape, and size in the scene.

TODAY'S CREATIVE ANGLE: "{angle}"
VISUAL MOOD: {mood}

Invent a specific, beautiful, realistic scene around this angle. Be creative and fresh.

CRITICAL REALISM RULES — the image must make physical sense:
- Tape and strips are DOUBLE-SIDED — they go on the BACK of an object between it and the wall. You NEVER see tape on the front face or top edge of a frame. If showing tape being applied, show it being pressed to the back of the frame or the wall surface.
- Hooks are mounted FLAT on the wall surface — items hang DOWN from the hook naturally by gravity. A bag hangs from a hook by its strap, a towel drapes over it, a plant pot hangs by a cord from it.
- Magnetic pads sit at the CORNERS behind a frame — they are not visible from the front, only as slim squares at the frame edge.
- Ask yourself: "Does this look physically possible in real life?" If not, fix it.

No retail packaging. No brand names or logos anywhere in the image.

Text overlay — bold white sans-serif, top-left or bottom-left corner:
{copy}

Perfect 1:1 square. Magazine quality."""

    contents = [prompt] + ref_image
    response = generate_image(contents)

    output_path = OUT_DIR / f"generated_post_{i}.png"

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
post_summary = f"{len(output_paths)} posts generated for {name}"
send_email_with_attachments(
    subject=f"Daily KLAPIT Creatives — {name} ({len(output_paths)} posts)",
    body=(
        f"Attached are today's {len(output_paths)} generated creatives for {name}.\n\n"
        f"Posts: {post_summary}"
    ),
    attachment_paths=output_paths,
)

print(f"\nEmail sent to {EMAIL_TO} with {len(output_paths)} image(s).")

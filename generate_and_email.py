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


# Visual styles — wide range of Instagram aesthetics
VISUAL_STYLES = [
    {
        "name": "Bright & Airy",
        "style": "bright white or off-white background, clean and fresh, light wood or marble accents, minimal props — feels like a Pinterest dream home",
        "lighting": "soft diffused natural daylight, even and bright, no harsh shadows",
        "people": False,
    },
    {
        "name": "Warm & Cozy Home",
        "style": "warm cream or terracotta tones, natural textures — linen, wood, rattan, stone — lived-in but beautifully styled, like a real home you want to live in",
        "lighting": "warm golden side light, soft organic shadows",
        "people": False,
    },
    {
        "name": "Dark & Luxury",
        "style": "deep charcoal, slate, or navy background, high contrast, gold or white typography, moody and editorial — feels like a premium brand campaign",
        "lighting": "single directional spotlight, dramatic but controlled shadows",
        "people": False,
    },
    {
        "name": "Real Person Moment",
        "style": "a real person naturally in the scene — hands pressing product to a wall, holding an item just hung, or enjoying a beautifully organized space. Feels candid and authentic, not posed.",
        "lighting": "natural warm indoor light, realistic and human",
        "people": True,
    },
    {
        "name": "Studio Product Hero",
        "style": "pure white or soft grey background, product is the only focus, long clean shadow beneath it — like an Apple product launch image",
        "lighting": "soft studio light from slightly above, perfectly even",
        "people": False,
    },
    {
        "name": "Aspirational Lifestyle Room",
        "style": "a full beautifully styled room — modern entryway, Scandinavian bathroom, minimal living room — product integrated naturally. Aspirational but achievable.",
        "lighting": "soft natural window light streaming in, warm and real",
        "people": False,
    },
    {
        "name": "Bold Color Block",
        "style": "one strong solid background color (dusty green, terracotta, cobalt, blush) — product pops against it, very graphic and design-forward, feels like a modern brand poster",
        "lighting": "flat even light, no shadows, graphic and clean",
        "people": False,
    },
    {
        "name": "Flat Lay Overhead",
        "style": "top-down flat lay view — product surrounded by 3-4 carefully chosen lifestyle items arranged with intentional white space on a clean surface (marble, wood, linen). Like a styled magazine spread shot from above.",
        "lighting": "bright overhead natural light, minimal shadows",
        "people": False,
    },
    {
        "name": "Golden Hour Glow",
        "style": "warm amber and honey tones, late-afternoon sunlight feel, shadows are long and golden, scene feels warm, inviting, and slightly cinematic",
        "lighting": "warm directional golden hour light from the side, rich and glowing",
        "people": False,
    },
    {
        "name": "Monochrome Minimal",
        "style": "single color family — all whites, all neutrals, all greys — product is the only element with contrast or color. Extremely clean, calm, and premium.",
        "lighting": "soft diffused light, almost shadowless, serene",
        "people": False,
    },
]

# Post concepts — wide range of Instagram content formats and storytelling angles
POST_CONCEPTS = [
    {
        "name": "POV Scroll-Stopper",
        "concept": "First-person POV format — the viewer IS the person in the scene. Frame it as a relatable moment: 'POV: You're moving into a new apartment and just discovered you never need to drill again.' The visual shows exactly what they would see. Bold, direct, scroll-stopping.",
        "text": "POV: [relatable situation specific to this product]. Make it 1-2 punchy lines that make someone stop scrolling.",
    },
    {
        "name": "Strength Stat Shock",
        "concept": "Lead with a jaw-dropping number — the product's weight capacity. Make it feel like a world record. Show something impressively heavy hanging confidently (a framed mirror, a coat, a bag) and let the stat do the talking. The visual PROVES the stat.",
        "text": "Giant bold number (the actual weight limit from product features) dominates the image. One line below like 'One strip. Serious hold.' — short and powerful.",
    },
    {
        "name": "Renter's Anthem",
        "concept": "Speak directly to renters — the #1 audience for this product. The visual should feel like the sigh of relief every renter feels when they find a damage-free solution. Could be a beautiful styled wall with the product, or someone confidently hanging something without a care.",
        "text": "Direct renter callout: 'Renters, this one's for you.' or 'No deposit lost. No holes. Just vibes.' — conversational and real.",
    },
    {
        "name": "The Satisfying Detail",
        "concept": "A close-up, satisfying shot focused on one specific detail — the product being pressed onto a clean tile, a hook holding a plant perfectly level, tape running cleanly along a rug edge. No wide shot needed. Make it feel ASMR-level satisfying.",
        "text": "Minimal text — just a short punchy line like 'Clean hold. Every time.' or 'This is what secure looks like.' placed simply in a corner.",
    },
    {
        "name": "The Quiet Upgrade",
        "concept": "Subtle aspirational content — 'quiet luxury' aesthetic. No loud claims. Just a beautifully styled space that looks incredible, and the KLAPiT product is simply part of it, doing its job invisibly. The vibe says: people with taste use this.",
        "text": "Ultra-minimal text. Just the product name or tagline in an elegant font. Let the image speak.",
    },
    {
        "name": "Did You Know",
        "concept": "Educational hook format. Lead with a surprising fact about the product or the problem it solves — most people don't know their walls can hold this much, or that nano-tape is reusable. Make it feel like a discovery the viewer wants to share.",
        "text": "Start with 'Did you know...' or 'Most people don't realize...' — finish with the surprising fact about this product's key feature.",
    },
    {
        "name": "The One Feature",
        "concept": "Dedicate the entire post to ONE standout feature of this specific product. Make that single feature feel extraordinary. Waterproof = show it in a steamy bathroom. Residue-free = pristine clean wall after removal. Reusable = effortless repositioning. One feature. Full commitment.",
        "text": "The feature as a bold one-word or two-word headline ('Waterproof.' / 'Zero Residue.' / 'Holds 60 LBS.'). One clean supporting sentence.",
    },
    {
        "name": "Before / After Split",
        "concept": "Clean two-panel split composition: LEFT shows the 'before' — a bare boring wall, a messy unorganized corner, or a nail-damaged surface. RIGHT shows the exact same space transformed with KLAPiT — styled, beautiful, organized. Both panels must look photographic and real.",
        "text": "'Before' label on the left panel. 'After' label on the right. Bold tagline centered at the bottom of the image: 'PEEL. STICK. DONE.'",
    },
    {
        "name": "Aesthetic Flat Lay",
        "concept": "A beautifully styled overhead flat lay — product packaging at the center, surrounded by 3-4 items that represent its world (a folded towel, small plant, set of keys, a frame). Every element placed with intention, lots of clean space. Feels like a lifestyle brand lookbook.",
        "text": "Product tagline placed cleanly below the arrangement. Minimal, confident — like a luxury product reveal.",
    },
    {
        "name": "Bold Typographic Poster",
        "concept": "Typography IS the art. Giant, impactful text takes up most of the image — one punchy headline in huge bold letters. The product is placed small but clearly visible as a supporting element. Feels like a modern editorial poster or campaign billboard.",
        "text": "One powerful 3-5 word headline in massive bold type. Examples: 'NO NAILS. NO LIMITS.' / 'HANG ANYTHING. DAMAGE NOTHING.' / 'YOUR WALLS. REIMAGINED.' — all caps, bold, impactful.",
    },
    {
        "name": "Room Glow-Up",
        "concept": "Aspirational room transformation — show a specific room (entryway, bedroom, bathroom, kitchen) at its most beautiful, with the product clearly responsible for one or more organized elements. Make the viewer think 'I want my home to look like this.'",
        "text": "Soft aspirational headline like 'This is your home on KLAPiT.' or 'Small product. Big glow-up.' — warm and inspiring.",
    },
    {
        "name": "The Hack You Need",
        "concept": "Position this as the ultimate home hack — one clever, specific use case that makes someone think 'why didn't I think of that?' Show the product solving a very specific real-life scenario relevant to its use cases. Feels like a viral life hack post.",
        "text": "Headline format: 'The [adjective] hack your [location] needs.' e.g. 'The bathroom hack you didn't know existed.' or 'The home office upgrade nobody told you about.'",
    },
    {
        "name": "Human Connection",
        "concept": "Warm, emotional storytelling — someone moving into their first apartment, a couple styling their new home, a parent organizing a child's room. The product is the simple, joyful answer to a real human moment. Authentic, warm, relatable.",
        "text": "Conversational first-person tone: 'Moving in? Leave the drill behind.' or 'We organized our whole entryway in 20 minutes.' — feels like a real person wrote it.",
    },
    {
        "name": "Minimal Product Drop",
        "concept": "Product-only focus — clean, confident, premium. Product packaging centered or off-center with dramatic negative space around it. A few perfectly chosen lifestyle props. Feels like a product launch announcement or a luxury brand's 'new drop' post.",
        "text": "Brand name bold at top, tagline at bottom. Nothing else. Silence can be powerful.",
    },
    {
        "name": "The Comparison Flex",
        "concept": "Side-by-side or implied comparison: traditional method (drill, nail, damage) vs. KLAPiT. Make the KLAPiT side obviously better — cleaner, easier, more beautiful. Not a messy infographic — a clean, beautiful visual comparison. KLAPiT always wins.",
        "text": "Simple comparison labels. Bold conclusion at the bottom: 'We're not the same.' or 'There's no competition.' — confident and witty.",
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

    people_note = "Include a real person naturally in this scene — hands pressing the product, partial body hanging an item, or a candid lifestyle moment. Authentic and human, not stock-photo staged." if style.get("people") else "No people in this image. Let the product and scene be the hero."

    prompt = f"""
You are a senior art director at a world-class Instagram marketing agency. Create one premium, scroll-stopping square Instagram post for KLAPiT — a modern home brand making nano-adhesive hooks, tapes, and strips that let people hang anything without drilling.

Audience: renters, home decor lovers, minimalists aged 25–40 who care about how their home looks.

━━━ YOUR EXACT SCENE TO CREATE ━━━
{scene}

This is the specific image you must produce. Execute it with full creative commitment — beautiful lighting, intentional composition, magazine-quality finish. Do NOT substitute a different scene.

━━━ PRODUCT IN THIS SCENE ━━━
The product being used: {name}
What it does: {description}
The product (hook / tape strip / magnetic pad) must be clearly visible doing its job in this scene. No retail packaging. No logo. The physical product only.

━━━ VISUAL MOOD ━━━
Aesthetic: {style["name"]} — {style["style"]}
Lighting: {style["lighting"]}
{people_note}

━━━ TEXT / COPY IN THE IMAGE ━━━
Format: {concept["name"]}
Direction: {concept["text"]}

Rules:
- Spell every word perfectly — zero tolerance for errors
- Bold clean sans-serif font (Helvetica / Futura style)
- Max 3 lines, high contrast against background
- Place text intentionally — top third or bottom third, never centre-blocking the scene

━━━ NON-NEGOTIABLE ━━━
- PERFECT SQUARE: 1:1 ratio
- No retail box or packaging anywhere
- No KLAPiT logo or brand name rendered in the image
- Premium and intentional — every element earns its place
"""

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

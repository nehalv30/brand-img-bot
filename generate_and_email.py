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
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

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


def crop_to_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def get_font(size: int) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()



def add_text_overlay(img: Image.Image, text: str) -> Image.Image:
    img = img.convert("RGBA")
    size = img.size[0]

    font_size = max(36, size // 18)
    font = get_font(font_size)
    lines = text.strip().split("\n")
    draw = ImageDraw.Draw(img)

    line_heights = [draw.textbbox((0, 0), l, font=font)[3] for l in lines]
    line_spacing = int(font_size * 0.3)
    block_h = sum(line_heights) + line_spacing * (len(lines) - 1)
    block_w = max(draw.textbbox((0, 0), l, font=font)[2] for l in lines)

    pad_x, pad_y = int(size * 0.05), int(size * 0.05)
    x = pad_x
    y = size - block_h - pad_y * 2

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle(
        [x - pad_x // 2, y - pad_y // 2,
         x + block_w + pad_x // 2, y + block_h + pad_y // 2],
        fill=(0, 0, 0, 150)
    )
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    cur_y = y
    for line in lines:
        draw.text((x, cur_y), line, font=font, fill=(255, 255, 255, 255))
        cur_y += draw.textbbox((0, 0), line, font=font)[3] + line_spacing

    return img.convert("RGB")


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
THEMES = [
    # Format: (angle, visual direction)
    ("Moving into your first place — bare walls, big dreams, zero budget for a contractor",
     "A fresh empty apartment, warm afternoon light, one or two items just hung on a clean wall"),
    ("Your landlord thinks you haven't touched the walls. You have.",
     "A beautifully decorated rental — gallery wall, hooks, mounted shelves — pristine walls, zero nail holes"),
    ("That corner you walked past every day and cringed at. Fixed.",
     "A previously ignored corner of a home now beautifully organised — hooks, frames, or shelves in place"),
    ("The kind of bathroom that makes you feel like you're at a boutique hotel",
     "A minimal spa-like bathroom, white tile, towels hanging from sleek hooks, warm morning light"),
    ("Sunday morning in the home you've always wanted",
     "A sun-filled living room or bedroom corner, beautifully styled, calm and aspirational"),
    ("Your entryway sets the mood for your whole day. Make it count.",
     "A styled modern apartment entryway — coat, bag, and keys each in their perfect place on the wall"),
    ("When guests arrive and ask 'wait, how is that hanging there?'",
     "A beautifully mounted piece — a large mirror, gallery wall, or floating shelf — with no visible hardware"),
    ("The before photo nobody wants to share. The after photo everyone saves.",
     "A split composition: LEFT messy bare wall or cluttered space; RIGHT the same space perfectly organised and styled"),
    ("A gallery wall that took 20 minutes and will cost you nothing to move",
     "A stunning gallery wall of 4-6 different frames arranged perfectly on a warm-toned wall, no nail holes"),
    ("Your rug keeps curling. Your guests keep tripping. Not anymore.",
     "A beautiful flat-lay view of a styled room — rug lying perfectly flat on hardwood floors, zero curl"),
    ("Kitchen goals: everything within reach, nothing in the way",
     "A beautifully organised kitchen — utensils, spice jars, or tools mounted neatly on the wall or cabinet sides"),
    ("Plant mum/dad level: hanging garden, zero holes in the ceiling",
     "Lush trailing plants hanging at different heights on a wall or near a window, hooks on the wall holding them"),
    ("5 minutes. A few strips. The whole room changed.",
     "A before/after or single styled shot showing a dramatic but simple home transformation"),
    ("Decorating without commitment — because your taste evolves",
     "A person casually rearranging frames on a wall with ease, warm candid moment, real home setting"),
    ("Heavy things. Clean walls. No compromise.",
     "Something impressively heavy — a large mirror, thick wooden frame, or heavy shelf — mounted perfectly on a clean wall"),
    ("The home that looks designed but cost nothing to change",
     "An editorial-quality styled room that looks like it belongs in a home magazine — clean, intentional, beautiful"),
    ("What your morning routine looks like when your home actually works",
     "A calm, organised morning scene — coat ready on a hook, keys hanging, bag in place — everything where it belongs"),
    ("Renters deserve beautiful homes too",
     "A beautifully styled rental apartment — art on walls, hooks, organised spaces — looking like an owned home"),
    ("The detail nobody notices but everyone feels",
     "An extreme close-up or detail shot of something mounted perfectly — a frame edge flush on a wall, a rug corner flat"),
    ("Organised is the new aesthetic",
     "A flat lay or room scene where everything is perfectly in its place — minimal, intentional, satisfying"),
]


def get_scene_for_product(product: dict, angle: str, visual: str) -> str:
    """Return a scene description grounded in what this product actually does."""
    folder = product["folder"]
    use_cases = ", ".join(product["use_cases"])

    if folder.startswith("KMHS"):
        what_it_does = "magnetic strips that mount pictures, clocks, and objects to walls with no nails — objects appear to float cleanly on the wall"
    elif folder.startswith("KSS") or folder.startswith("KST"):
        what_it_does = "clear double-sided nano tape that mounts frames, secures rugs flat, and holds shelves — completely invisible once applied"
    elif folder.startswith("KSH"):
        what_it_does = "small adhesive wall hooks that hold towels, coats, bags, plants, and kitchen items — hooks press flat on any wall surface"
    else:
        what_it_does = f"adhesive home organizer used for: {use_cases}"

    return f"{visual}. The scene should naturally show the result of using {what_it_does}. Use cases shown: {use_cases}."


def get_copy_lines(product: dict) -> list[str]:
    """Return punchy copy lines tailored to this product type."""
    folder = product["folder"]
    if folder.startswith("KMHS"):
        return [
            "Float it on the wall.\nNo nails. No kidding.",
            "Walls that work for you.\nZero holes required.",
            "Magnetic hold.\nClean finish.",
            "Heavy things. Clean walls.\nNo compromise.",
            "Mount it. Move it.\nRepeat.",
        ]
    elif folder.startswith("KSS") or folder.startswith("KST"):
        return [
            "Invisible hold.\nVisible results.",
            "Flat floors. Happy home.\nZero trace.",
            "Peel. Press. Perfect.\nEvery time.",
            "Secure it. Style it.\nLeave no mark.",
            "The tape that disappears.\nThe results that don't.",
        ]
    elif folder.startswith("KSH"):
        return [
            "Hang it. Love it.\nKeep your deposit.",
            "No screws.\nNo excuses.",
            "Your walls finally\nwork for you.",
            "Hook it up.\nNo tools needed.",
            "Everything in its place.\nZero damage.",
        ]
    else:
        return [
            "No nails. No limits.\nJust results.",
            "Your home. Your rules.\nZero holes.",
            "Stick it. Style it.\nLeave nothing behind.",
            "5 minutes.\nZero tools. This.",
            "Clean hold.\nEvery time.",
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

# Pick 3 unique themes and copy lines for today
themes_today = rng.sample(THEMES, 3)
copy_lines = get_copy_lines(product)
copies_today = rng.sample(copy_lines, min(3, len(copy_lines)))

print(f"Today's themes: {', '.join(t[0][:50] for t in themes_today)}\n")

# Generate one image per theme
output_paths = []

for i, ((angle, visual), copy) in enumerate(zip(themes_today, copies_today), 1):
    print(f"Generating image {i}/3 — {angle[:60]} ...")

    scene = get_scene_for_product(product, angle, visual)

    prompt = f"""Professional Instagram lifestyle photo. Square format.

SCENE: {scene}

THEME: {angle}

Render this as a beautiful, realistic, magazine-quality home photo. The scene must make complete sense — every object in the frame has a reason to be there. Aspirational but achievable. No text, no logos, no brand names, no packaging anywhere in the image. No awkward AI-looking hands or poses."""

    contents = [prompt]
    response = generate_image(contents)

    output_path = OUT_DIR / f"generated_post_{i}.png"

    saved = False
    for part in response.parts:
        if getattr(part, "inline_data", None) is not None:
            raw_image = part.as_image()
            final_image = crop_to_square(raw_image)
            final_image = add_text_overlay(final_image, copy)
            final_image.save(output_path)
            print(f"  Saved: {output_path.name}")
            output_paths.append(output_path)
            saved = True
            break
        elif getattr(part, "text", None):
            print(f"  Model said: {part.text}")

    if not saved:
        print(f"  Warning: No image returned for angle '{angle}'")

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

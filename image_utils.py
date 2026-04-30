from io import BytesIO
from pathlib import Path

from google.genai import types
from PIL import Image, ImageDraw, ImageFont


def pil_to_part(img: Image.Image) -> types.Part:
    """Convert a PIL Image to a Gemini API Part (JPEG, single conversion point)."""
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=85)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def get_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for fp in candidates:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def crop_to_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def add_text_overlay(img: Image.Image, text: str) -> Image.Image:
    img = img.convert("RGBA")
    size = img.size[0]

    font_size = max(36, size // 18)
    font = get_font(font_size)
    lines = text.strip().split("\n")
    draw = ImageDraw.Draw(img)

    line_heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in lines]
    line_spacing = int(font_size * 0.3)
    block_h = sum(line_heights) + line_spacing * (len(lines) - 1)
    block_w = max(draw.textbbox((0, 0), ln, font=font)[2] for ln in lines)

    pad_x = int(size * 0.05)
    pad_y = int(size * 0.05)
    x = pad_x
    y = size - block_h - pad_y * 2

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle(
        [x - pad_x // 2, y - pad_y // 2,
         x + block_w + pad_x // 2, y + block_h + pad_y // 2],
        fill=(0, 0, 0, 150),
    )
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    cur_y = y
    for ln in lines:
        draw.text((x, cur_y), ln, font=font, fill=(255, 255, 255, 255))
        cur_y += draw.textbbox((0, 0), ln, font=font)[3] + line_spacing

    return img.convert("RGB")

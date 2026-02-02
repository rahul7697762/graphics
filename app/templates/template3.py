import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ==================================================
# PATH HANDLING
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# ==================================================
# CONFIG
# ==================================================
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "outputs")
CANVAS_SIZE = (1080, 1350)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==================================================
# CONSTANTS
# ==================================================
SHADOW_COLOR = (0, 0, 0, 90)
SHADOW_OFFSET = (0, 3)

TICK = "."
AMENITY_COLOR = "#222"
TICK_COLOR = "#000000"

# ==================================================
# FONT LOADER
# ==================================================
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# ==================================================
# ICON / LOGO
# ==================================================
def load_icon(path, size=(28, 28)):
    if not path or not os.path.exists(path):
        return None
    return Image.open(path).convert("RGBA").resize(size)

def load_logo(path, size=(120, 120)):
    if not path or not os.path.exists(path):
        return None
    return Image.open(path).convert("RGBA").resize(size)

# ==================================================
# TEXT HELPERS
# ==================================================
def draw_text_with_shadow(
    draw,
    position,
    text,
    font,
    fill,
    shadow_offset=(0, 3),
    shadow_fill=(0, 0, 0, 90)
):
    x, y = position
    ox, oy = shadow_offset

    draw.text((x + ox, y + oy), text, font=font, fill=shadow_fill, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")

def draw_amenities(
    draw,
    amenities,
    font,
    start_x,
    start_y,
    max_width,
    line_height=48,
    max_per_column=4
):
    col_gap = 60
    col_width = max_width // 2

    for idx, amenity in enumerate(amenities):
        col = idx // max_per_column
        row = idx % max_per_column

        x = start_x + col * (col_width + col_gap)
        y = start_y + row * line_height

        draw.text((x, y), TICK, font=font, fill=TICK_COLOR)
        draw.text((x + 28, y), amenity, font=font, fill=AMENITY_COLOR)

# ==================================================
# TEMPLATE RENDER FUNCTION (DESIGN UNCHANGED)
# ==================================================
def render(bg_path: str, content: dict, data: dict, job_id: str) -> str:
    """
    Render poster using template 3.
    Design is intentionally unchanged.
    """

    canvas = Image.new("RGBA", CANVAS_SIZE)
    bg = Image.open(bg_path).convert("RGBA").resize(CANVAS_SIZE)
    canvas.paste(bg, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # ---------- FONTS ----------
    title_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Cinzel-ExtraBold.ttf"), 95
    )
    subtitle_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Regular.ttf"), 40
    )
    amenity_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Roboto_Condensed-SemiBold.ttf"), 50
    )
    phone_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 60
    )
    cta_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Oswald-Bold.ttf"), 50
    )

    # ---------- TITLE ----------
    draw_text_with_shadow(
        draw,
        (540, 120),
        content["title"],
        title_font,
        "white",
        shadow_offset=(6, 6),
        shadow_fill=(0, 0, 0, 255)
    )

    draw_text_with_shadow(
        draw,
        (540, 210),
        content["subline"],
        subtitle_font,
        "#eeeeee",
        shadow_offset=(0, 2),
        shadow_fill=(0, 0, 0, 190)
    )

    # ---------- INFO CARD ----------
    card_size = (900, 440)
    CARD_ALPHA = 150

    card = Image.new("RGBA", card_size, (255, 255, 255, 255))
    mask = Image.new("L", card_size, CARD_ALPHA)

    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        (0, 0, card_size[0], card_size[1]),
        radius=27,
        fill=CARD_ALPHA
    )

    card.putalpha(mask)
    canvas.paste(card, (90, 770), card)

    draw_amenities(
        draw,
        content["amenities"],
        amenity_font,
        start_x=140,
        start_y=900,
        max_width=720
    )

    # ---------- CTA RIBBON ----------
    ribbon_w, ribbon_h = 600, 80
    ribbon = Image.new("RGBA", (ribbon_w, ribbon_h), (200, 30, 30, 255))

    mask = Image.new("L", (ribbon_w, ribbon_h), 255)
    mask_draw = ImageDraw.Draw(mask)

    cut = 35
    mask_draw.polygon(
        [(ribbon_w, 0), (ribbon_w - cut, ribbon_h // 2), (ribbon_w, ribbon_h)],
        fill=0
    )
    ribbon.putalpha(mask)

    rdraw = ImageDraw.Draw(ribbon)
    bbox = rdraw.textbbox((0, 0), content["cta"], font=cta_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    rdraw.text(
        ((ribbon_w - cut - tw) // 2, (ribbon_h - th) // 2 - 20),
        content["cta"],
        font=cta_font,
        fill="white"
    )

    shadow = Image.new("RGBA", (ribbon_w, ribbon_h), (0, 0, 0, 100))
    shadow.putalpha(mask)

    shadow = shadow.rotate(8, expand=True).filter(ImageFilter.GaussianBlur(8))
    ribbon = ribbon.rotate(8, expand=True)

    shadow = shadow.crop(shadow.getbbox())
    ribbon = ribbon.crop(ribbon.getbbox())

    canvas.paste(shadow, (-5, 648), shadow)
    canvas.paste(ribbon, (-10, 630), ribbon)

    # ---------- FOOTER ----------
    footer = Image.new("RGBA", (1080, 140), (15, 30, 50, 255))
    canvas.paste(footer, (0, 1210))

    draw.text((250, 1240), data["phone"], font=phone_font, fill="white")

    call_icon = load_icon(
        os.path.join(PROJECT_ROOT, "assets", "call.png"),
        size=(110, 110)
    )
    if call_icon:
        canvas.paste(call_icon, (145, 1220), call_icon)

    logo = load_logo(data.get("logo_path"), size=(230, 110))
    if logo:
        canvas.paste(logo, (800, 1220), logo)

    # ---------- SAVE ----------
    output_path = os.path.join(
        OUTPUT_FOLDER,
        f"poster_{job_id}.png"
    )
    canvas.save(output_path)

    return output_path
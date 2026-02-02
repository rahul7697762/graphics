import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ==================================================
# PATH HANDLING (ADDED)
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
# UTILS
# ==================================================
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_center(draw, xy, text, font, fill):
    draw.text(xy, text, font=font, fill=fill, anchor="mm", align="center")

# ==================================================
# TEMPLATE RENDER FUNCTION (DESIGN UNCHANGED)
# ==================================================
def render(bg_path: str, content: dict, data: dict, job_id: str) -> str:
    """
    Render poster using template 2.
    Design is intentionally unchanged.
    """

    base = Image.open(bg_path).convert("RGBA").resize(CANVAS_SIZE)
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)

    # ==================================================
    # FONTS
    # ==================================================
    title_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-SemiBold.ttf"), 80
    )
    price_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 52
    )
    amenity_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 30
    )
    cta_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 36
    )

    # ==================================================
    # LOAD TICK ICON
    # ==================================================
    tick = Image.open(
        os.path.join(PROJECT_ROOT, "assets", "tick2.png")
    ).convert("RGBA")
    tick_size = 28
    tick = tick.resize((tick_size, tick_size), Image.LANCZOS)

    # ==================================================
    # HEADER
    # ==================================================
    draw_center(draw, (540, 90), content["title"], title_font, (255, 255, 255))
    draw.line([(250, 170), (800, 170)], fill=(255, 220, 255, 200), width=2)

    # ==================================================
    # GLASS CARD (REAL GLASSMORPHISM)
    # ==================================================
    card_w, card_h = 820, 190
    card_x = (CANVAS_SIZE[0] - card_w) // 2
    card_y = 880
    radius = 32

    blurred_bg = base.crop(
        (card_x, card_y, card_x + card_w, card_y + card_h)
    ).filter(ImageFilter.GaussianBlur(10))

    card_mask = Image.new("L", (card_w, card_h), 0)
    mask_draw = ImageDraw.Draw(card_mask)
    mask_draw.rounded_rectangle(
        [0, 0, card_w, card_h],
        radius=radius,
        fill=255
    )

    glass = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 30))
    glass = Image.composite(blurred_bg, glass, card_mask)
    canvas.paste(glass, (card_x, card_y), card_mask)

    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.rounded_rectangle(
        [
            card_x - 8,
            card_y - 8,
            card_x + card_w + 8,
            card_y + card_h + 8
        ],
        radius=radius + 6,
        fill=(120, 200, 255, 0)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    canvas = Image.alpha_composite(canvas, glow)
    draw = ImageDraw.Draw(canvas)

    glow_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow_layer)

    g.rounded_rectangle(
        [
            card_x - 6,
            card_y - 6,
            card_x + card_w + 6,
            card_y + card_h + 6
        ],
        radius=radius + 6,
        outline=(0, 180, 255, 255),
        width=10
    )

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(12))
    canvas = Image.alpha_composite(canvas, glow_layer)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=radius,
        outline=(0, 220, 255, 200),
        width=4
    )

    # ==================================================
    # PRICE TEXT
    # ==================================================
    draw_center(
        draw,
        (540, card_y + card_h // 2),
        f"{data['bhk']}\nSTARTING FROM {data['price']}",
        price_font,
        (255, 255, 255)
    )

    # ==================================================
    # PRE-LAUNCH TAG
    # ==================================================
    tag = Image.new("RGBA", (250, 100), (210, 40, 40, 255))
    tag_draw = ImageDraw.Draw(tag)
    tag_draw.multiline_text(
        (120, 40),
        "EXCLUSIVE\nPRE-LAUNCH",
        font=amenity_font,
        fill="white",
        anchor="mm",
        align="center"
    )
    tag = tag.rotate(+8, expand=True)
    canvas.paste(tag, (170, card_y - 120), tag)

    # ==================================================
    # AMENITIES (WITH TICK ICON)
    # ==================================================
    left_x, right_x = 250, 620
    start_y = 1150
    icon_gap = 14
    text_offset = tick_size + icon_gap

    amenities = content["amenities"]
    left_items = amenities[:2]
    right_items = amenities[2:4]

    y = start_y
    for item in left_items:
        canvas.paste(tick, (left_x - text_offset, y + 4), tick)
        draw.text((left_x, y), item, fill=(255, 255, 255), font=amenity_font)
        y += 42

    y = start_y
    for item in right_items:
        canvas.paste(tick, (right_x - text_offset, y + 4), tick)
        draw.text((right_x, y), item, fill=(255, 255, 255), font=amenity_font)
        y += 42

    # ==================================================
    # CTA BUTTON
    # ==================================================
    cta_w, cta_h = 420, 80
    cta = Image.new("RGBA", (cta_w, cta_h), (0, 0, 0, 0))

    cta_mask = Image.new("L", (cta_w, cta_h), 0)
    cta_mask_draw = ImageDraw.Draw(cta_mask)
    cta_mask_draw.rounded_rectangle(
        [0, 0, cta_w, cta_h],
        radius=cta_h // 2,
        fill=255
    )

    cta_bg = Image.new("RGBA", (cta_w, cta_h), (220, 40, 40, 255))
    cta_bg.putalpha(cta_mask)
    cta = Image.alpha_composite(cta, cta_bg)

    cta_draw = ImageDraw.Draw(cta)
    cta_draw.text(
        (cta_w // 2, cta_h // 2 - 2),
        data["phone"],
        fill="white",
        font=cta_font,
        anchor="mm"
    )

    canvas.paste(
        cta,
        ((CANVAS_SIZE[0] - cta_w) // 2, 1250),
        cta
    )

    # ==================================================
    # FOOTER
    # ==================================================
    draw_center(
        draw,
        (540, 210),
        "LOTLITE REAL ESTATE",
        amenity_font,
        (255, 255, 255)
    )

    output_path = os.path.join(
        OUTPUT_FOLDER,
        f"poster_{job_id}.png"
    )
    canvas.save(output_path)

    return output_path


# ==================================================
# LOCAL TEST CALL (OPTIONAL)
# ==================================================
if __name__ == "__main__":
    bg = os.path.join(PROJECT_ROOT, "outputs", "background.png")

    dummy_content = {
        "title": "CODEX RESIDENCIES",
        "amenities": ["Smart Home", "3 & 4 BHK", "Sky Deck", "Panoramic Views"]
    }

    dummy_data = {
        "bhk": "LUXURY FLATS",
        "price": "₹9.75 CR",
        "phone": "+91 90111 35889"
    }

    out = render(bg, dummy_content, dummy_data, "local_test")
    print("Generated:", out)
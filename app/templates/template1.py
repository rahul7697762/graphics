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
CANVAS_SIZE = (1080, 1350)
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

AMENITY_COLOR = "#F1F1F1"

# Load tick icon ONCE
TICK_ICON = Image.open(
    os.path.join(PROJECT_ROOT, "assets", "tick.png")
).convert("RGBA").resize((24, 24))


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
def load_icon(path, size=(90, 90)):
    if not path or not os.path.exists(path):
        return None
    return Image.open(path).convert("RGBA").resize(size)


def load_logo(path, size=(220, 110)):
    if not path or not os.path.exists(path):
        return None
    return Image.open(path).convert("RGBA").resize(size)


# ==================================================
# TEXT WITH SHADOW
# ==================================================
def draw_text_with_shadow(draw, pos, text, font, fill):
    x, y = pos
    draw.text((x, y + 3), text, font=font, fill=(0, 0, 0, 220), anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


# ==================================================
# AMENITIES (HORIZONTAL + WRAPPED + PNG TICK)
# ==================================================
def draw_amenities_horizontal_wrapped(
    canvas,
    draw,
    items,
    font,
    start_x,
    start_y,
    max_width,
    icon_size=24,
    gap=16,
    row_gap=12
):
    x, y = start_x, start_y

    for item in items:
        text_width = draw.textlength(item, font=font)
        total_width = icon_size + gap + text_width + 30

        if x + total_width > start_x + max_width:
            x = start_x
            y += font.size + row_gap

        canvas.paste(
            TICK_ICON,
            (int(x), int(y + 6)),
            TICK_ICON
        )

        draw.text(
            (int(x + icon_size + gap), int(y)),
            item,
            font=font,
            fill=AMENITY_COLOR
        )

        x += total_width


# ==================================================
# DARK GRADIENT
# ==================================================
def add_bottom_gradient(canvas, height=520):
    grad = Image.new("L", (1, height))
    for y in range(height):
        grad.putpixel((0, y), int(255 * (y / height)))

    grad = grad.resize((CANVAS_SIZE[0], height))
    black = Image.new("RGBA", (CANVAS_SIZE[0], height), (0, 0, 0, 255))
    black.putalpha(grad)
    canvas.paste(black, (0, CANVAS_SIZE[1] - height), black)


# ==================================================
# TEMPLATE RENDER FUNCTION (DESIGN UNCHANGED)
# ==================================================
def render(bg_path: str, content: dict, data: dict, job_id: str) -> str:
    """
    Render poster using template 1.
    Design is intentionally unchanged.
    """

    canvas = Image.new("RGBA", CANVAS_SIZE)
    bg = Image.open(bg_path).convert("RGBA").resize(CANVAS_SIZE)
    canvas.paste(bg, (0, 0))

    add_bottom_gradient(canvas)
    draw = ImageDraw.Draw(canvas)

    # ---------------- FONTS ----------------
    title_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Cinzel-ExtraBold.ttf"), 70
    )
    subtitle_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Regular.ttf"), 36
    )
    price_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 44
    )
    amenity_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Roboto_Condensed-SemiBold.ttf"), 36
    )
    phone_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 56
    )
    cta_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Oswald-Bold.ttf"), 42
    )

    # ---------------- HEADER ----------------
    draw_text_with_shadow(draw, (540, 120), content["title"], title_font, "white")
    draw_text_with_shadow(
        draw,
        (540, 200),
        content["subline"].upper(),
        subtitle_font,
        "#E63946"
    )

    price = f"{data['bhk']}  |  {data['price']}"
    draw_text_with_shadow(draw, (540, 260), price, price_font, "white")

    # ---------------- CTA RIBBON ----------------
    cta_text = content["cta"]

    ribbon_w, ribbon_h = 600, 78
    ribbon_color = (200, 30, 30, 255)

    ribbon = Image.new("RGBA", (ribbon_w, ribbon_h), ribbon_color)

    mask = Image.new("L", (ribbon_w, ribbon_h), 255)
    mdraw = ImageDraw.Draw(mask)
    cut = 35

    mdraw.polygon(
        [(ribbon_w, 0), (ribbon_w - cut, ribbon_h // 2), (ribbon_w, ribbon_h)],
        fill=0
    )
    ribbon.putalpha(mask)

    rdraw = ImageDraw.Draw(ribbon)
    tw = rdraw.textlength(cta_text, font=cta_font)
    tx = (ribbon_w - cut - tw) // 2
    ty = (ribbon_h - cta_font.size) // 2 - 4

    rdraw.text((tx, ty), cta_text, font=cta_font, fill="white")

    ribbon = ribbon.rotate(8, expand=True, resample=Image.Resampling.BICUBIC)
    ribbon = ribbon.crop(ribbon.getbbox())

    canvas.paste(ribbon, (-10, 620), ribbon)

    # ---------------- AMENITIES ----------------
    draw_amenities_horizontal_wrapped(
        canvas,
        draw,
        content["amenities"],
        amenity_font,
        start_x=120,
        start_y=1000,
        max_width=840
    )

    # ---------------- FOOTER ----------------
    footer = Image.new("RGBA", (1080, 90), (200, 30, 30, 255))
    canvas.paste(footer, (0, 1150))

    icon = load_icon(
        os.path.join(PROJECT_ROOT, "assets", "call.png")
    )
    if icon:
        canvas.paste(icon, (220, 1160), icon)

    draw.text((330, 1170), data["phone"], font=phone_font, fill="white")

    # ---------------- SAVE ----------------
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
    dummy_bg = os.path.join(PROJECT_ROOT, "outputs", "background.png")

    dummy_content = {
        "title": "LUXURY REDEFINED",
        "subline": "PREMIUM HOMES AT PUNE",
        "amenities": ["Infinity Pool", "Gym", "Clubhouse"],
        "cta": "BOOK NOW"
    }

    dummy_data = {
        "bhk": "3 & 4 BHK",
        "price": "₹2.5 Cr Onwards",
        "phone": "+91 98765 43210"
    }

    out = render(
        bg_path=dummy_bg,
        content=dummy_content,
        data=dummy_data,
        job_id="local_test"
    )

    print("Image generated at:", out)
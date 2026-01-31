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
CANVAS_SIZE = (1080, 1920)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==================================================
# HELPERS
# ==================================================
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def get_wrapped_text(text, font, max_pixel_width):
    words = text.split()
    lines, current = [], []

    for word in words:
        test = " ".join(current + [word])
        try:
            width = font.getlength(test)
        except AttributeError:
            bbox = font.getbbox(test)
            width = bbox[2] - bbox[0]

        if width <= max_pixel_width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return "\n".join(lines)

def load_icon(path, size=(110, 110)):
    if not path or not os.path.exists(path):
        return None
    return Image.open(path).convert("RGBA").resize(size)

def load_logo(path, size=(360, 180)):
    if not path or not os.path.exists(path):
        return None
    return Image.open(path).convert("RGBA").resize(size)

# ==================================================
# TEMPLATE RENDER FUNCTION (DESIGN UNCHANGED)
# ==================================================
def render(bg_path: str, content: dict, data: dict, job_id: str) -> str:
    """
    Render poster using template 4.
    Design is intentionally unchanged.
    """

    # --------------------------------------------------
    # LOAD BASE TEMPLATE
    # --------------------------------------------------
    template_path = os.path.join(PROJECT_ROOT, "templates", "template2.png")
    template = Image.open(template_path).convert("RGBA")

    bg = Image.open(bg_path).convert("RGBA")

    W, H = template.size
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))

    # --------------------------------------------------
    # BACKGROUND + GRADIENT
    # --------------------------------------------------
    bg_resized = bg.resize((W, 1200), Image.Resampling.LANCZOS)
    canvas.paste(bg_resized, (0, 0))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    DARK_BLUE = (12, 48, 80)
    grad_height = 600

    for y in range(grad_height):
        alpha = int(240 * (1 - (y / grad_height) ** 1.2))
        overlay_draw.line(
            [(0, y), (W, y)],
            fill=(DARK_BLUE[0], DARK_BLUE[1], DARK_BLUE[2], alpha)
        )

    canvas = Image.alpha_composite(canvas, overlay)
    canvas = Image.alpha_composite(canvas, template)

    draw = ImageDraw.Draw(canvas)

    # --------------------------------------------------
    # FONTS
    # --------------------------------------------------
    title_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Cinzel-ExtraBold.ttf"), 95
    )
    subtitle_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "DMSerifDisplay-Italic.ttf"), 70
    )
    amenity_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Inter-Medium.ttf"), 40
    )
    phone_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-SemiBold.ttf"), 85
    )
    sub2_font = load_font(
        os.path.join(PROJECT_ROOT, "fonts", "Montserrat-Bold.ttf"), 80
    )

    WHITE = (255, 255, 255)
    RED = (200, 30, 30)

    # --------------------------------------------------
    # LOGO
    # --------------------------------------------------
    logo = load_logo(data.get("logo_path"))
    if logo:
        canvas.paste(logo, (50, 1800), logo)

    # --------------------------------------------------
    # TITLE
    # --------------------------------------------------
    title = content["title"]
    t_bbox = draw.textbbox((0, 0), title, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    draw.text(((W - t_w) // 2, 20), title, fill=WHITE, font=title_font)

    # --------------------------------------------------
    # SUBLINE
    # --------------------------------------------------
    wrapped_sub = get_wrapped_text(
        content["subline"], subtitle_font, 1000
    )

    s_bbox = draw.multiline_textbbox(
        (0, 0), wrapped_sub, font=subtitle_font, spacing=10
    )
    s_w = s_bbox[2] - s_bbox[0]

    draw.multiline_text(
        ((W - s_w) // 2, 1500),
        wrapped_sub,
        fill=WHITE,
        font=subtitle_font,
        spacing=10,
        align="center"
    )

    # --------------------------------------------------
    # SUBLINE 2
    # --------------------------------------------------
    sub2 = content.get("subline2", "")
    s2_bbox = draw.textbbox((0, 0), sub2, font=sub2_font)
    s2_w = s2_bbox[2] - s2_bbox[0]

    draw.text(
        ((W - s2_w) // 2, 1600),
        sub2,
        fill=(255, 215, 0),
        font=sub2_font
    )

    # --------------------------------------------------
    # AMENITIES
    # --------------------------------------------------
    amenity_y = [1150, 1270, 1390]
    amenity_x = 250

    for text, y in zip(content["amenities"][:3], amenity_y):
        bbox = draw.textbbox((0, 0), text, font=amenity_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        padding_x, padding_y = 40, 15
        rect = [
            amenity_x - w // 2 - padding_x,
            y - h // 2 - padding_y,
            amenity_x + w // 2 + padding_x,
            y + h // 2 + padding_y
        ]

        draw.rectangle(rect, fill=RED)
        draw.text(
            (amenity_x - w // 2, y - h // 2 - 4),
            text,
            fill=WHITE,
            font=amenity_font
        )

    # --------------------------------------------------
    # FOOTER
    # --------------------------------------------------
    draw.text((770, 1800), data["phone"], fill=WHITE, font=phone_font)

    call_icon = load_icon(
        os.path.join(PROJECT_ROOT, "assets", "call.png")
    )
    if call_icon:
        canvas.paste(call_icon, (640, 1760), call_icon)

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------
    output_path = os.path.join(
        OUTPUT_FOLDER,
        f"poster_{job_id}.png"
    )
    canvas.save(output_path)

    return output_path

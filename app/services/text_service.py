def generate_marketing_text(text_model, data: dict) -> dict:
    """
    Generate marketing copy using Gemini
    """

    user_amenities = ", ".join(data.get("amenities", []))

    prompt = f"""
You are a senior real estate copywriter.

User provided amenities keywords:
{user_amenities}

Rules:
- TITLE short
- SUBLINE offer or location driven
- AMENITIES only 6 max 3 words
- CTA BOOK NOW limited offer
- No fullstops

Return format:
TITLE:
SUBLINE:
AMENITIES:
-
-
-
CTA:
"""

    res = text_model.generate_content(prompt)
    raw = res.text.replace("```", "").strip()

    result = {
        "title": "",
        "subline": "",
        "amenities": [],
        "cta": ""
    }

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            result["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("SUBLINE:"):
            result["subline"] = line.split(":", 1)[1].strip()
        elif line.startswith("-"):
            result["amenities"].append(line.replace("-", "").strip())
        elif line.startswith("CTA:"):
            result["cta"] = line.split(":", 1)[1].strip().upper()

    # ---- FALLBACKS ----
    if not result["title"]:
        result["title"] = "LUXURY REDEFINED"
    if not result["subline"]:
        result["subline"] = f"PREMIUM HOMES AT {data['location'].upper()}"
    if not result["amenities"]:
        result["amenities"] = ["Infinity Pool", "Gymnasium", "Clubhouse"]
    if not result["cta"]:
        result["cta"] = "BOOK NOW"

    return result

import os
from dotenv import load_dotenv

load_dotenv()

def generate_marketing_text(text_model, data: dict) -> dict:
    """
    Generate marketing copy using Gemini or return mock text
    """
    
    # Check for mock mode
    if os.getenv("MOCK_AI", "false").lower() == "true" or text_model == "mock_text_model":
        print("⚠️ MOCK MODE: Using placeholder marketing text")
        amenities = data.get("amenities", ["Infinity Pool", "Smart Home", "Private Garden"])[:6]
        bhk = data.get("bhk", "2 & 3 BHK")
        return {
            "title": f"LUXURY {data.get('property_type', 'LIVING').upper()}",
            "subline": f"{bhk} Premium Residences at {data.get('location', 'Prime Location')}",
            "subline2": data.get("price", "Price on Request"),
            "amenities": amenities if isinstance(amenities, list) else ["Infinity Pool", "Gymnasium", "Clubhouse"],
            "cta": "BOOK NOW",
            "builder": data.get("builder", ""),
            "address": data.get("address", ""),
            "email": data.get("email", ""),
            "bhk": bhk
        }

    # Extract all property details for AI
    user_amenities = ", ".join(data.get("amenities", []))
    property_type = data.get("property_type", "Luxury Apartments")
    location = data.get("location", "Premium Location")
    price = data.get("price", "Contact for Price")
    bhk = data.get("bhk", "2 & 3 BHK")
    builder = data.get("builder", "")
    address = data.get("address", "")

    prompt = f"""
You are a senior real estate copywriter creating marketing content for urban property.

Property Details:
- Type: {property_type}
- Location: {location}
- BHK: {bhk}
- Price: {price}
- Builder: {builder}
- Address: {address}
- Amenities: {user_amenities}

Rules:
- TITLE: Short, powerful headline (max 4 words)
- SUBLINE: Include BHK and location, compelling offer
- SUBLINE2: Price or value proposition
- AMENITIES: List 6 key features (max 3 words each)
- CTA: Urgent call to action
- No fullstops

Return format:
TITLE:
SUBLINE:
SUBLINE2:
AMENITIES:
-
-
-
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
        "subline2": "",
        "amenities": [],
        "cta": ""
    }

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            result["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("SUBLINE2:"):
            result["subline2"] = line.split(":", 1)[1].strip()
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
        result["subline"] = f"{data.get('bhk', '2 & 3 BHK')} PREMIUM HOMES AT {data['location'].upper()}"
    if not result["subline2"]:
        result["subline2"] = data.get("price", "Price on Request")
    if not result["amenities"]:
        result["amenities"] = ["Infinity Pool", "Gymnasium", "Clubhouse"]
    if not result["cta"]:
        result["cta"] = "BOOK NOW"

    return result
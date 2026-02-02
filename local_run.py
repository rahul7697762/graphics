import os
from uuid import uuid4

from app.services.vertex import init_vertex
from app.services.image_service import generate_background
from app.services.text_service import generate_marketing_text
from app.templates import template1

# --------------------------------------------------
# USER INPUT (simulate frontend)
# --------------------------------------------------
data = {
    "property_type": "Luxury Apartments",
    "location": "Pune",
    "price": "₹2.5 Cr Onwards",
    "bhk": "3 & 4 BHK",
    "phone": "+91 98765 43210",
    "amenities": ["Pool", "Gym", "Clubhouse"]
}

# --------------------------------------------------
# INIT MODELS
# --------------------------------------------------
models = init_vertex()

# --------------------------------------------------
# 1️⃣ Generate background using IMAGEN
# --------------------------------------------------
bg_path = generate_background(
    image_model=models["image"],
    property_type=data["property_type"]
)

print("Background generated:", bg_path)

# --------------------------------------------------
# 2️⃣ Generate marketing text using GEMINI
# --------------------------------------------------
content = generate_marketing_text(
    text_model=models["text"],
    data=data
)

print("Marketing text generated")

# --------------------------------------------------
# 3️⃣ Render template
# --------------------------------------------------
output_path = template1.render(
    bg_path=bg_path,
    content=content,
    data=data,
    job_id=str(uuid4())
)

print("Final poster generated:", output_path)

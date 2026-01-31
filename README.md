🎨 AI Graphic Generator (Production Ready)

An AI-powered system to generate premium marketing creatives (real estate / banquet halls / properties) using Vertex AI (Imagen + Gemini) and Pillow-based design templates.

This project is structured for backend API usage and frontend integration, with support for multiple templates and random selection.

🚀 Features

🧠 AI-generated background images (Vertex Imagen)

✍️ AI-generated marketing copy (Gemini)

🎨 Multiple design templates (Pillow-based)

🎲 Random template selection

⚙️ Backend-ready architecture

🧩 Frontend-friendly API contract

🔒 Secure (no secrets in repo)




POST /generate
Request Body{
  "property_type": "Luxury Apartments",
  "location": "Pune",
  "price": "₹2.5 Cr Onwards",
  "bhk": "3 & 4 BHK",
  "phone": "+91 98765 43210",
  "amenities": ["Pool", "Gym", "Clubhouse"],
  "template": "random"
}


Response
{
  "status": "success",
  "image_path": "/outputs/poster_12345.png"
}

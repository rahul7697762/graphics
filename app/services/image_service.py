import os
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def generate_background(image_model, property_type: str, location: str = "") -> str:
    """
    Generate background image using Imagen or return mock image
    """
    
    # Check for mock mode
    if os.getenv("MOCK_AI", "false").lower() == "true" or image_model == "mock_image_model":
        print("⚠️ MOCK MODE: Using placeholder background image")
        path = os.path.join(OUTPUT_FOLDER, "background.png")
        
        # Create a placeholder image if it doesn't exist
        if not os.path.exists(path):
            # Create a gradient placeholder (1080x1920)
            img = Image.new("RGB", (1080, 1920), (30, 60, 90))
            img.save(path)
            print(f"Created placeholder background at: {path}")
        
        return path
    
    # Urban real estate focused prompt
    prompt = (
        f"Premium urban {property_type} in {location if location else 'modern city'}, "
        "stunning high-rise residential tower, contemporary glass and steel architecture, "
        "city skyline background, luxury apartment building, modern urban development, "
        "golden hour lighting, professional real estate photography, "
        "no text, no logos, no watermarks, vertical poster format"
    )

    res = image_model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="9:16"
    )

    path = os.path.join(OUTPUT_FOLDER, "background.png")
    res.images[0].save(location=path)

    return path
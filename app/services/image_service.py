import os

OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def generate_background(image_model, property_type: str) -> str:
    """
    Generate background image using Imagen
    """
    prompt = (
        f"Ultra luxury {property_type}, cinematic architectural photography, "
        "golden hour sunset, bright sky upper half, dark foreground lower half, "
        "no text, no logos, vertical poster"
    )

    res = image_model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="9:16"
    )

    path = os.path.join(OUTPUT_FOLDER, "background.png")
    res.images[0].save(location=path)

    return path

import os
from dotenv import load_dotenv

import vertexai
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel
from vertexai.preview.vision_models import ImageGenerationModel


def init_vertex():
    """
    Initialize Vertex AI models using environment variables
    """

    # Load .env only in local/dev
    load_dotenv()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not all([project_id, location, cred_path]):
        raise RuntimeError(
            "Missing Vertex AI environment variables"
        )

    credentials = service_account.Credentials.from_service_account_file(
        cred_path
    )

    vertexai.init(
        project=project_id,
        location=location,
        credentials=credentials
    )

    # ---- MODELS ----
    text_model = GenerativeModel("gemini-2.0-flash")

    image_model = ImageGenerationModel.from_pretrained(
        "imagen-3.0-generate-002"
    )

    return {
        "text": text_model,
        "image": image_model
    }

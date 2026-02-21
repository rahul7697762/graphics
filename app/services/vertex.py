import os
from dotenv import load_dotenv

def init_vertex():
    """
    Initialize Vertex AI models using environment variables
    """

    # Load .env only in local/dev
    load_dotenv()

    # ---- MOCK MODE CHECK ----
    if os.getenv("MOCK_AI", "false").lower() == "true":
        print("⚠️ RUNNING IN MOCK AI MODE (No Vertex AI connection) ⚠️")
        return {
            "text": "mock_text_model",
            "image": "mock_image_model"
        }

    # ---- SSL FIX FOR CORPORATE PROXIES ----
    import ssl
    import certifi
    import httplib2
    
    # Set SSL certificate path from certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = certifi.where()
    
    # Configure httplib2 to use certifi certs
    httplib2.CA_CERTS = certifi.where()

    import vertexai
    from google.oauth2 import service_account
    from vertexai.generative_models import GenerativeModel
    from vertexai.preview.vision_models import ImageGenerationModel

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    cred_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    if not all([project_id, location]) or (not cred_path and not cred_json):
        raise RuntimeError(
            "Missing Vertex AI environment variables. Need PROJECT, LOCATION, and either CREDENTIALS (path) or CREDENTIALS_JSON (content)"
        )

    if cred_json:
        # Preferred: Load from JSON string env var (GOOGLE_APPLICATION_CREDENTIALS_JSON)
        import json
        try:
            info = json.loads(cred_json)
            credentials = service_account.Credentials.from_service_account_info(info)
            print("✅ Loaded credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {str(e)}")
    elif cred_path and cred_path.strip().startswith("{"):
        # Fallback: GOOGLE_APPLICATION_CREDENTIALS contains raw JSON (not a file path)
        import json
        try:
            info = json.loads(cred_path)
            credentials = service_account.Credentials.from_service_account_info(info)
            print("✅ Loaded credentials from GOOGLE_APPLICATION_CREDENTIALS (JSON content)")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS: {str(e)}")
    else:
        # Local dev: GOOGLE_APPLICATION_CREDENTIALS is a file path
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        print(f"✅ Loaded credentials from file: {cred_path}")


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

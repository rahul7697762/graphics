import sys
import os

sys.path.append(os.getcwd())

print("Checking imports...")

try:
    from app.models import GenerateResponse
    print("GenerateResponse found.")
except ImportError:
    print("GenerateResponse NOT found.")
except Exception as e:
    print(f"Error importing GenerateResponse: {e}")

try:
    from app.template_selector import pick_template
    print("pick_template imported successfully.")
except ImportError as e:
    print(f"ImportError in template_selector: {e}")
except Exception as e:
    print(f"Error importing pick_template: {e}")

import sys
import json
import os
import traceback
from uuid import uuid4

# Add current directory to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.vertex import init_vertex
from app.services.image_service import generate_background
from app.services.text_service import generate_marketing_text
from app.template_selector import pick_template
from app.models import GenerateRequest, GenerateResponse 

class StdoutRedirector:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = sys.stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout 

def main():
    try:
        # 1. Parse Input
        if len(sys.argv) < 2:
            raise ValueError("No input data provided")
        
        raw_input = sys.argv[1]
        data = json.loads(raw_input)
        
        # Redirect stdout to avoid pollution from libraries
        with StdoutRedirector():
             # 2. Init AI Models
             # Ensure .env is loaded (init_vertex does this)
             models = init_vertex()
        
             # Validate/Default keys required by template1
             if "bhk" not in data:
                 data["bhk"] = "2 & 3 BHK" # Default to avoid KeyError
             if "amenities" not in data:
                  data["amenities"] = ["Premium Utilities", "24/7 Security", "Parking"]
     
             # Validate using Pydantic Model
             request_model = GenerateRequest(**data)
             validated_data = request_model.model_dump()
     
             # 3. Generate Background
             # Map frontend "property_type" to backend expectation
             bg_path = generate_background(
                 image_model=models["image"], 
                 property_type=validated_data["property_type"]
             )
             
             # 4. Generate Text
             # We need to reshape data for text service if needed
             # text_service expects 'amenities' list
             # frontend sends amenities as array
             content = generate_marketing_text(
                 text_model=models["text"],
                 data=validated_data
             )
             
             # 5. Render Template
             # Select template dynamically based on input or random
             template_id = validated_data.get("template_id", "random")
             template_fn = pick_template(template_id)
             job_id = str(uuid4())
             
             output_path = template_fn(
                 bg_path=bg_path,
                 content=content,
                 data=validated_data,
                 job_id=job_id
             )
        
        # 6. Success Output (Formatted as GenerateResponse)
        response = GenerateResponse(
            success=True,
            status="success",
            image_url=output_path,
            template_used=template_fn.__name__
        )
        print(response.model_dump_json())

    except Exception as e:
        # Error Output
        error_res = {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }
        print(json.dumps(error_res))

if __name__ == "__main__":
    main()

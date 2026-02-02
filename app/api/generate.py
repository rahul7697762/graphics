from fastapi import APIRouter, HTTPException
from uuid import uuid4

from app.models import GenerateRequest, GenerateResponse
from app.services.vertex import init_vertex
from app.services.image_service import generate_background
from app.services.text_service import generate_marketing_text
from app.template_selector import pick_template

router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
def generate_poster(request: GenerateRequest):
    """
    Generate marketing poster based on user input
    """

    try:
        # --------------------------------------------
        # 1. Init AI models
        # --------------------------------------------
        models = init_vertex()

        # --------------------------------------------
        # 2. Generate background image
        # --------------------------------------------
        bg_path = generate_background(
            image_model=models["image"],
            property_type=request.property_type,
            location=request.location
        )

        # --------------------------------------------
        # 3. Generate marketing text
        # --------------------------------------------
        content = generate_marketing_text(
            text_model=models["text"],
            data=request.dict()
        )

        # --------------------------------------------
        # 4. Pick template (random or user selected)
        # --------------------------------------------
        template_fn = pick_template(request.template_id)

        # --------------------------------------------
        # 5. Render poster
        # --------------------------------------------
        output_path = template_fn(
            bg_path=bg_path,
            content=content,
            data=request.dict(),
            job_id=str(uuid4())
        )

        # --------------------------------------------
        # 6. Return response
        # --------------------------------------------
        return GenerateResponse(
            success=True,
            status="success",
            image_url=output_path,
            template_used=template_fn.__name__
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

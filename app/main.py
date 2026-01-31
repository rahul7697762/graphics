from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.generate import router as generate_router

# ==================================================
# APP INITIALIZATION
# ==================================================

app = FastAPI(
    title="Graphic Generator API",
    description="AI powered poster generator",
    version="1.0.0"
)

# ==================================================
# CORS (frontend access)
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict later in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# ROUTES
# ==================================================

app.include_router(generate_router, prefix="/api")

# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "graphic_generator"
    }

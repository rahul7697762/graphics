"""
Blog Generation API Router — internal service only.
Called by the Node.js server; Node.js already verified the JWT.
Python does NOT re-verify auth — this is an internal microservice.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load main .env file from the Ai-agents directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import requests as _requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import blog_ai_service as ai

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST MODEL
# ─────────────────────────────────────────────────────────────────────────────

class GenerateBlogRequest(BaseModel):
    topic: Optional[str] = None
    industry: Optional[str] = None
    keywords: Optional[str] = ""
    language: Optional[str] = "English"
    style: Optional[str] = "Professional"
    length: Optional[str] = "Medium (500-1000 words)"
    audience: Optional[str] = "General Public"
    image_option: Optional[str] = "auto"    # auto | custom | none
    custom_image_url: Optional[str] = None
    wp_url: Optional[str] = None            # website URL for interlinking
    interlinks: Optional[list] = None       # pre-built interlinks from Node.js [{title, link}]


LENGTH_MAPPING = {
    "Short (300-500 words)": 300,
    "Medium (500-1000 words)": 500,
    "Long (1000-2000 words)": 1000,
}


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE ENDPOINT  (no auth — internal service called by Node.js only)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_blog(body: GenerateBlogRequest):
    """
    Runs the full AI generation pipeline and returns JSON.
    Auth is handled upstream by Node.js. This endpoint is internal-only.
    """
    topic = body.topic
    keywords = body.keywords or ""

    # ── 1. Industry mode: auto-generate topic + keywords ──────────────────────
    if not topic and body.industry:
        idea = ai.generate_title_and_keywords(body.industry)
        topic = idea["topic"]
        keywords = idea["keywords"]

    if not topic:
        raise HTTPException(status_code=400, detail="topic or industry is required")

    # ── 2. Keyword generation ─────────────────────────────────────────────────
    if not keywords.strip():
        try:
            keywords = ai.generate_keywords(topic)
        except Exception as e:
            print(f"Perplexity keywords failed, falling back to OpenAI: {e}")
            keywords = ai.openai_generate_keywords(topic)

    # ── 3. WordPress interlinks (optional) ────────────────────────────────────
    # Use pre-built interlinks if provided by Node.js (e.g. from Supabase articles)
    if body.interlinks:
        interlinks = body.interlinks
        print(f"Using {len(interlinks)} pre-built interlinks from server")
    elif body.wp_url:
        interlinks = []
        try:
            base_url = body.wp_url.rstrip("/")
            if not base_url.startswith("http"):
                base_url = f"https://{base_url}"
            wp_res = _requests.get(
                f"{base_url}/wp-json/wp/v2/posts?per_page=10", timeout=10
            )
            content_type = wp_res.headers.get("Content-Type", "")
            if wp_res.status_code == 200 and "application/json" in content_type:
                posts = wp_res.json()
                if isinstance(posts, list):
                    interlinks = [
                        {"title": p["title"]["rendered"], "link": p["link"]}
                        for p in posts
                        if "title" in p and "link" in p
                    ]
                    print(f"WP interlinks fetched: {len(interlinks)} posts from {base_url}")
            else:
                print(f"WP interlinks skipped: {base_url} returned status={wp_res.status_code}, content-type={content_type!r} (not a WordPress REST API endpoint)")
        except Exception as e:
            print(f"WP interlinks fetch failed for {body.wp_url}: {type(e).__name__}: {e}")
    else:
        interlinks = []

    # ── 4. Content generation ─────────────────────────────────────────────────
    length_num = LENGTH_MAPPING.get(body.length, 500)
    try:
        content_result = ai.generate_blog_content(
            topic, keywords, body.language, body.audience, body.style,
            length_num, interlinks
        )
    except Exception as e:
        print(f"Perplexity content gen failed, falling back to OpenAI: {e}")
        content_result = ai.openai_generate_blog_content(
            topic, keywords, body.language, body.audience, body.style,
            length_num, interlinks
        )

    blog_text = content_result["blogText"]
    word_count = content_result["wordCount"]

    # ── 5. SEO title ──────────────────────────────────────────────────────────
    seo_title = ai.generate_seo_title(blog_text, topic)

    # ── 6. Plagiarism check ───────────────────────────────────────────────────
    plagiarism_check = ai.check_plagiarism(blog_text)

    # ── 7. Image ──────────────────────────────────────────────────────────────
    image_url = None
    if body.image_option == "auto":
        try:
            image_text = ai.generate_image_text(blog_text, topic)
            image_url = ai.generate_image(topic, image_text)  # raw OpenAI URL
        except Exception as e:
            print(f"Image generation failed: {e}")
    elif body.image_option == "custom":
        image_url = body.custom_image_url

    # ── 8. Convert Markdown → HTML ────────────────────────────────────────────
    blog_html = ai.format_markdown_to_html(blog_text)

    # ── 9. Return everything — Node.js handles persistence ────────────────────
    return {
        "success": True,
        "article": blog_html,          # HTML content
        "markdown": blog_text,         # raw Markdown
        "seoTitle": seo_title,
        "imageUrl": image_url,         # raw URL (Node.js should upload to storage)
        "wordCount": word_count,
        "plagiarismCheck": plagiarism_check,
        "topic": topic,
        "keywords": keywords,
    }

"""
Blog AI Service
Handles all AI-powered generation via Perplexity (sonar-pro), OpenAI fallback (GPT-4o),
and Google Gemini Imagen 3 for image generation.
Ported from Node.js: perplexityService.js + openAIService.js

Research tasks (topic discovery, keyword research, plagiarism checking) are
handled by LangChain SERP tools (serp_tools.py) backed by SerpAPI.
Perplexity / OpenAI remain as fallback when SERP_API_KEY is not set.
"""

import os
import json
import requests
from typing import Optional


PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")

# Import SERP tools — will be None if the module fails to load
try:
    from app.services.serp_tools import (
        trending_topics_tool,
        keyword_research_tool,
        plagiarism_check_tool,
    )
    _SERP_AVAILABLE = bool(os.getenv("SERP_API_KEY"))
except Exception as _serp_import_err:  # pragma: no cover
    print(f"serp_tools import failed, SERP disabled: {_serp_import_err}")
    _SERP_AVAILABLE = False

PERPLEXITY_BASE_URL = "https://api.perplexity.ai/chat/completions"
OPENAI_CHAT_URL     = "https://api.openai.com/v1/chat/completions"


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _perplexity_call(user_prompt: str, system_msg: str = "You are an expert.", max_tokens: int = 4000, model: str = "sonar-pro") -> str:
    """Make a single call to Perplexity and return the text content."""
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "n": 1,
    }
    res = requests.post(PERPLEXITY_BASE_URL, headers=headers, json=payload, timeout=120)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


def _openai_chat_call(user_prompt: str, system_msg: str = "You are an expert.", max_tokens: int = 4000) -> str:
    """Make a single call to OpenAI GPT-4o and return the text content."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "n": 1,
    }
    res = requests.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=120)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────────────────────────────────────
# PERPLEXITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def generate_title_and_keywords(industry: str) -> dict:
    """
    Auto-generate a blog topic + keyword list for a given industry.
    Uses SerpAPI (real Google data) when SERP_API_KEY is set,
    falls back to Perplexity sonar-pro otherwise.
    Returns: {"topic": str, "keywords": str}
    """
    if _SERP_AVAILABLE:
        try:
            result = trending_topics_tool.run(industry)
            # tool returns a dict; BaseTool.run may stringify it
            if isinstance(result, str):
                result = json.loads(result)
            print(f"generate_title_and_keywords: used SerpAPI for '{industry}'")
            return result
        except Exception as e:
            print(f"SerpAPI trending topics failed, falling back to Perplexity: {e}")

    prompt = (
        f'Act as an SEO expert. For the industry "{industry}", suggest a high-potential, '
        f'trending blog post Topic (Title) and a list of 5 relevant Keywords that would rank well.\n'
        f'Format exactly as JSON:\n'
        f'{{"topic": "The exact title of the blog post", "keywords": "keyword1, keyword2, keyword3, keyword4, keyword5"}}'
    )
    try:
        raw = _perplexity_call(prompt, "You are an SEO expert.", max_tokens=500)
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"Perplexity industry idea error: {e}")
        return {
            "topic": f"Top trends in {industry}",
            "keywords": f"{industry}, trends, news, update, guide",
        }


def generate_keywords(topic: str) -> str:
    """
    Return a comma-separated list of SEO keywords for the given topic.
    Uses SerpAPI (real related searches + PAA) when SERP_API_KEY is set,
    falls back to Perplexity sonar-pro otherwise.
    """
    if _SERP_AVAILABLE:
        try:
            result = keyword_research_tool.run(topic)
            print(f"generate_keywords: used SerpAPI for '{topic}'")
            return result
        except Exception as e:
            print(f"SerpAPI keyword research failed, falling back to Perplexity: {e}")

    prompt = (
        f'You are an SEO keyword research expert. For the topic "{topic}", generate 8–12 high-value keywords.\n'
        f'Include: 1 primary keyword (exact match), 3–4 long-tail variations (3+ words), 2–3 LSI/semantic keywords, 1–2 question-based keywords (e.g. "how to...", "what is...").\n'
        f'Return ONLY a comma-separated list of keywords. No explanations, no numbering, no headers.'
    )
    return _perplexity_call(prompt, "You are an SEO expert.", max_tokens=200)


def generate_blog_content(
    topic: str,
    keywords: str,
    language: str,
    audience: str,
    style: str,
    length_num: int,
    interlinks: Optional[list] = None,
    max_attempts: int = 3,
    model_variant: str = "A",  # A=Perplexity sonar-pro, B=OpenAI GPT-4o (A/B test)
) -> dict:
    """
    Generate full blog content using Perplexity sonar-pro.
    Retries until word count reaches length_num (up to max_attempts).
    Returns: {"blogText": str, "wordCount": int}
    """
    interlinks = interlinks or []
    blog_text = ""
    word_count = 0
    current_attempts = 0

    # Build interlinking instructions
    interlink_instructions = ""
    if interlinks:
        links_str = "\n".join(
            [f'- "{lnk["title"]}" → {lnk["link"]}' for lnk in interlinks]
        )
        interlink_instructions = f"""
        ══ MANDATORY INTERNAL LINKING (STRICT) ══
        You MUST naturally hyperlink to ALL of the following pages somewhere in the article body.
        Rules:
        1. Embed each link as a Markdown hyperlink: [anchor text](URL) — use a relevant keyword as anchor, NOT the raw URL.
        2. Place each link inside a sentence in a paragraph (NOT in a heading, NOT in a list at the end).
        3. Example of correct format: "...similar to what we discussed in our guide on [AI lead qualification](https://example.com/page)..."
        4. Do NOT add any other external links. These are the ONLY links allowed.
        5. Failure to include ALL links below will result in rejection.

        Links to embed:
        {links_str}
        ═════════════════════════════════════════
        """

    while word_count < length_num and current_attempts < max_attempts:
        current_attempts += 1
        continuation = (
            f"Continue strictly from previous text: {blog_text[-100:]}"
            if blog_text
            else "Start from the beginning."
        )

        primary_keyword = keywords.split(",")[0].strip() if keywords else topic

        prompt = f"""
        You are an expert SEO content writer and professional blogger. Your goal is to write a comprehensive, high-ranking blog post that dominates search engine results pages (SERPs).

        TOPIC: "{topic}"
        PRIMARY KEYWORD: "{primary_keyword}"
        ALL KEYWORDS TO USE: {keywords or "none"}
        TARGET AUDIENCE: {audience}
        LANGUAGE: {language}
        WRITING STYLE: {style}
        MINIMUM WORD COUNT: {length_num}

        ══ SEO STRUCTURE REQUIREMENTS ══
        Use this exact heading hierarchy:
        # [H1: Include primary keyword near the beginning — this is the page title]
        ## [H2: Main section headings — include keyword variations]
        ### [H3: Subsection headings — include LSI keywords]

        MANDATORY ARTICLE STRUCTURE:
        1. **H1 Title** — Primary keyword within first 5 words
        2. **Intro paragraph (100–150 words)** — Include the primary keyword in the very first sentence. Hook the reader with a compelling question or statistic. Briefly state what the reader will learn.
        3. **4–6 H2 sections** — Each covering a distinct, valuable subtopic. Begin each section with a keyword-rich sentence.
        4. **FAQ Section (H2: "Frequently Asked Questions")** — Add 3–5 Q&A pairs targeting "People Also Ask" queries related to "{topic}". Format: ### Question\\n Answer paragraph.
        5. **Conclusion with CTA (H2: "Final Thoughts" or "Conclusion")** — Summarise key takeaways, restate the primary keyword, and end with a clear call-to-action.

        ══ KEYWORD PLACEMENT RULES (CRITICAL FOR SEO) ══
        - Primary keyword must appear in: the H1 title, first paragraph (within first 100 words), at least 2 H2 headings, and the conclusion.
        - Keyword density: 1–2% — use naturally, never stuff.
        - Use LSI (semantically related) keywords throughout body paragraphs.
        - Use **bold** to highlight the primary keyword on first use in the body.

        ══ CONTENT QUALITY RULES ══
        - Write in {style.lower()} tone, first-person perspective where it adds authenticity.
        - Every section must deliver genuine value — no filler, no padding.
        - Include specific facts, numbers, or actionable tips in each section.
        - Use short paragraphs (3–5 sentences max) for readability.
        - Use bullet points or numbered lists where appropriate (they get featured snippets).
        - Use **bold** for key terms and *italic* for emphasis sparingly.

        {interlink_instructions}

        ⚠️ STRICT RULES:
        - Do NOT use [1], [2] citation numbers or academic references.
        - {"ONLY use the internal links listed above — no other external URLs." if interlinks else "Do NOT add any external links or URLs anywhere in the content."}
        - Do NOT use generic filler phrases like "In conclusion, as we have seen..."
        - {continuation}

        Output clean, valid Markdown only. No preamble, no meta-commentary.
        """

        if model_variant == "B":
            # A/B variant B: Perplexity sonar (lighter model)
            new_content = _perplexity_call(prompt, "You are an expert SEO content writer.", max_tokens=6000, model="sonar")
        else:
            # A/B variant A (control): Perplexity sonar-pro
            new_content = _perplexity_call(prompt, "You are an expert SEO content writer.", max_tokens=6000)

        blog_text += "\n\n" + new_content
        word_count = len(blog_text.split())

    return {"blogText": blog_text.strip(), "wordCount": word_count, "modelVariant": model_variant}


def generate_seo_title(blog_text: str, topic: str) -> str:
    """Generate an SEO-optimised title from blog content."""
    import re
    prompt = (
        f"Based on this blog content, generate ONE perfect SEO title tag for this blog post.\n"
        f"Topic: {topic}\n\n"
        f"Content preview:\n{blog_text[:1200]}\n\n"
        f"SEO Title Rules:\n"
        f"- Return ONLY the title itself — no quotes, no explanations, no extra text.\n"
        f"- Place the PRIMARY keyword as close to the beginning of the title as possible.\n"
        f"- Keep it between 50–60 characters (search engines truncate beyond 60).\n"
        f"- Make it compelling and click-worthy — it appears as the clickable headline in Google results.\n"
        f"- Do NOT include character counts, annotations like '(37 chars)', or numbering like '1.'.\n"
        f"- Do NOT use clickbait or misleading language — accurately reflect the content.\n"
        f"- Use a power word or number if it fits naturally (e.g. 'Best', 'Complete Guide', '7 Tips')."
    )
    try:
        raw = _perplexity_call(prompt, "You are an expert SEO copywriter.", max_tokens=60).strip()
        # Strip any (xx chars) / [xx chars] / (xx characters) annotations the model may add
        title = re.sub(r'[\(\[]\d+\s*(?:chars?|characters?)[\)\]]', '', raw, flags=re.IGNORECASE).strip()
        # Strip surrounding quotes if the model wrapped the title
        title = title.strip('"\'')
        return title if title else topic
    except Exception as e:
        print(f"Perplexity SEO title error: {e}")
        return topic


def check_plagiarism(blog_text: str) -> str:
    """
    Check plagiarism. Returns a human-readable result string.
    Uses SerpAPI (real Google exact-phrase search) when SERP_API_KEY is set,
    falls back to Perplexity sonar-pro otherwise.
    """
    if not blog_text or not blog_text.strip():
        return "Plagiarism check skipped - empty content"

    if _SERP_AVAILABLE:
        try:
            result = plagiarism_check_tool.run(blog_text)
            print("check_plagiarism: used SerpAPI exact-phrase search")
            return result
        except Exception as e:
            print(f"SerpAPI plagiarism check failed, falling back to Perplexity: {e}")

    prompt = (
        f'Check for plagiarism in this article. Reply "No plagiarism detected" if original, '
        f"otherwise summarize detected parts:\n\n{blog_text[:3000]}"
    )
    try:
        result = _perplexity_call(prompt, "You are a plagiarism checker.", max_tokens=500).strip()
        if "no plagiarism" not in result.lower():
            result += " ⚠️ Could not fully eliminate plagiarism, but the article is returned to user."
        return result
    except Exception as e:
        print(f"Perplexity plagiarism error: {e}")
        return "Plagiarism check unavailable - service error"


def generate_image_text(blog_text: str, topic: str) -> str:
    """Generate a short (≤3 word) catchy headline for a blog header image."""
    prompt = (
        f"Based on this blog content, create a short, simplest, small and catchy headline or phrase "
        f"(maximum 3 words) that would look good on a blog header image. "
        f"Make it engaging and relevant to the content:\n{blog_text[:1000]}\n"
        f"Topic: {topic}\nReturn only the headline text, nothing else."
    )
    try:
        text = _perplexity_call(
            prompt,
            "You are a marketing copywriter expert at creating catchy headlines.",
            max_tokens=100,
        ).strip()
        return text.replace('"', "").replace("'", "").strip()
    except Exception as e:
        print(f"Perplexity image text error: {e}")
        return topic


# ─────────────────────────────────────────────────────────────────────────────
# OPENAI FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def openai_generate_keywords(topic: str) -> str:
    """Fallback keyword generation via OpenAI GPT-4o."""
    prompt = (
        f'You are an SEO keyword research expert. For the topic "{topic}", generate 8–12 high-value keywords.\n'
        f'Include: 1 primary keyword (exact match), 3–4 long-tail variations (3+ words), 2–3 LSI/semantic keywords, 1–2 question-based keywords (e.g. "how to...", "what is...").\n'
        f'Return ONLY a comma-separated list of keywords. No explanations, no numbering, no headers.'
    )
    try:
        return _openai_chat_call(prompt, "You are an SEO expert.", max_tokens=200)
    except Exception as e:
        print(f"OpenAI keyword error: {e}")
        return ""


def openai_generate_blog_content(
    topic: str,
    keywords: str,
    language: str,
    audience: str,
    style: str,
    length_num: int,
    interlinks: Optional[list] = None,
) -> dict:
    """Fallback blog content generation via OpenAI GPT-4o."""
    interlinks = interlinks or []

    interlink_instructions = ""
    if interlinks:
        links_str = "\n".join(
            [f'- "{lnk["title"]}" → {lnk["link"]}' for lnk in interlinks]
        )
        interlink_instructions = f"""
        ══ MANDATORY INTERNAL LINKING (STRICT) ══
        You MUST naturally hyperlink to ALL of the following pages somewhere in the article body.
        Rules:
        1. Embed each link as a Markdown hyperlink: [anchor text](URL) — use a relevant keyword as anchor, NOT the raw URL.
        2. Place each link inside a sentence in a paragraph (NOT in a heading, NOT in a list at the end).
        3. Example of correct format: "...similar to what we discussed in our guide on [AI lead qualification](https://example.com/page)..."
        4. Do NOT add any other external links. These are the ONLY links allowed.
        5. Failure to include ALL links below will result in rejection.

        Links to embed:
        {links_str}
        ═════════════════════════════════════════
        """

    primary_keyword = keywords.split(",")[0].strip() if keywords else topic

    prompt = f"""
    You are an expert SEO content writer and professional blogger. Your goal is to write a comprehensive, high-ranking blog post that dominates search engine results pages (SERPs).

    TOPIC: "{topic}"
    PRIMARY KEYWORD: "{primary_keyword}"
    ALL KEYWORDS TO USE: {keywords or "none"}
    TARGET AUDIENCE: {audience}
    LANGUAGE: {language}
    WRITING STYLE: {style}
    MINIMUM WORD COUNT: {length_num}

    ══ SEO STRUCTURE REQUIREMENTS ══
    Use this exact heading hierarchy:
    # [H1: Include primary keyword near the beginning — this is the page title]
    ## [H2: Main section headings — include keyword variations]
    ### [H3: Subsection headings — include LSI keywords]

    MANDATORY ARTICLE STRUCTURE:
    1. **H1 Title** — Primary keyword within first 5 words
    2. **Intro paragraph (100–150 words)** — Include the primary keyword in the very first sentence. Hook the reader with a compelling question or statistic. Briefly state what the reader will learn.
    3. **4–6 H2 sections** — Each covering a distinct, valuable subtopic. Begin each section with a keyword-rich sentence.
    4. **FAQ Section (H2: "Frequently Asked Questions")** — Add 3–5 Q&A pairs targeting "People Also Ask" queries related to "{topic}". Format: ### Question\\n Answer paragraph.
    5. **Conclusion with CTA (H2: "Final Thoughts" or "Conclusion")** — Summarise key takeaways, restate the primary keyword, and end with a clear call-to-action.

    ══ KEYWORD PLACEMENT RULES (CRITICAL FOR SEO) ══
    - Primary keyword must appear in: the H1 title, first paragraph (within first 100 words), at least 2 H2 headings, and the conclusion.
    - Keyword density: 1–2% — use naturally, never stuff.
    - Use LSI (semantically related) keywords throughout body paragraphs.
    - Use **bold** to highlight the primary keyword on first use in the body.

    ══ CONTENT QUALITY RULES ══
    - Write in {style.lower()} tone, first-person perspective where it adds authenticity.
    - Every section must deliver genuine value — no filler, no padding.
    - Include specific facts, numbers, or actionable tips in each section.
    - Use short paragraphs (3–5 sentences max) for readability.
    - Use bullet points or numbered lists where appropriate (they get featured snippets).
    - Use **bold** for key terms and *italic* for emphasis sparingly.

    {interlink_instructions}

    ⚠️ STRICT RULES:
    - Do NOT use [1], [2] citation numbers or academic references.
    - {"ONLY use the internal links listed above — no other external URLs." if interlinks else "Do NOT add any external links or URLs anywhere in the content."}
    - Do NOT use generic filler phrases like "In conclusion, as we have seen..."
    """

    blog_text = _openai_chat_call(prompt, "You are an expert SEO content writer.", max_tokens=6000)
    return {"blogText": blog_text.strip(), "wordCount": len(blog_text.split())}


def generate_image(topic: str, image_text: str) -> str:
    """
    Generate a blog header image.
    Strategy:
      1. Vertex AI Imagen 3 via ImageGenerationModel.from_pretrained (uses service account)
         → returns base64 data URI
      2. Fall back to OpenAI DALL-E 3 → returns image URL string
      3. Fall back to a solid-colour placeholder base64 PNG
    """
    import base64
    import io

    prompt = (
        f"Create a professional, text-free blog header image about: {topic}. "
        f"Visual requirements: high-quality modern design, landscape orientation (16:9), "
        f"clean professional appearance suitable for blog publication. "
        f"CRITICAL: Do not include ANY text, words, letters, watermarks, signs, logos, or typography anywhere in the image."
    )

    # ── 1. Vertex AI Imagen 3 (via service account) ───────────────────────────
    try:
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel
        from google.oauth2 import service_account

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location   = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        cred_path  = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        cred_json  = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")

        # Load credentials (JSON string takes precedence over file path)
        if cred_json:
            import json as _json
            credentials = service_account.Credentials.from_service_account_info(
                _json.loads(cred_json)
            )
        elif cred_path and not cred_path.strip().startswith("{"):
            credentials = service_account.Credentials.from_service_account_file(cred_path)
        else:
            credentials = None  # let ADC handle it

        vertexai.init(project=project_id, location=location, credentials=credentials)

        image_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        response = image_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
        )

        if response.images:
            img_bytes = response.images[0]._image_bytes
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            print(f"Image generated via Vertex AI Imagen 3 for: {topic}")
            return f"data:image/png;base64,{b64}"
        else:
            raise RuntimeError("Vertex AI Imagen returned no images")

    except Exception as e:
        print(f"Vertex AI Imagen failed: {type(e).__name__}: {e}. Trying OpenAI DALL-E...")

    # ── 2. Fall back to OpenAI DALL-E 3 ──────────────────────────────────────
    if OPENAI_API_KEY:
        try:
            dalle_prompt = (
                f"Professional, text-free blog header image about: {topic}. "
                f"Modern landscape design, clean and photorealistic. "
                f"CRITICAL: No text, no words, no letters, no typography, no watermarks, no signs, no logos."
            )
            res = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "dall-e-3", "prompt": dalle_prompt, "n": 1, "size": "1792x1024", "response_format": "url"},
                timeout=60,
            )
            res.raise_for_status()
            url = res.json()["data"][0]["url"]
            print(f"Image generated via OpenAI DALL-E 3 for: {topic}")
            return url
        except Exception as e:
            print(f"OpenAI DALL-E failed: {type(e).__name__}: {e}")

    # ── 3. Solid-colour placeholder ───────────────────────────────────────────
    print("All image generation methods failed. Returning placeholder.")
    from PIL import Image as _PILImage
    img = _PILImage.new("RGB", (1280, 720), (30, 58, 138))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ─────────────────────────────────────────────────────────────────────────────
# HTML FORMATTER (shared utility)
# ─────────────────────────────────────────────────────────────────────────────

def format_markdown_to_html(text: str) -> str:
    """Convert Markdown blog text to semantic HTML."""
    import re
    html = text

    # Strip any leading/trailing whitespace
    html = html.strip()

    # Headings — order matters: longest prefix first to avoid partial matches
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$',  r'<h3>\1</h3>',  html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$',   r'<h2>\1</h2>',   html, flags=re.MULTILINE)
    # H1: convert to <h1> and strip any stray leading '#' that wasn't converted
    html = re.sub(r'^# (.+)$',    r'<h1>\1</h1>',    html, flags=re.MULTILINE)

    # Inline formatting
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         html)

    # Hyperlinks
    html = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener noreferrer" style="color: #2563eb; text-decoration: underline;">\1</a>',
        html,
    )

    # Bullet lists: convert lines starting with "- " or "* " into <ul><li> blocks
    def _replace_list_block(m):
        items = re.sub(r'^[-*] (.+)$', r'<li>\1</li>', m.group(0), flags=re.MULTILINE)
        return f'<ul>{items}</ul>'
    html = re.sub(r'(^[-*] .+$\n?)+', _replace_list_block, html, flags=re.MULTILINE)

    # Numbered lists: convert lines starting with "1. " "2. " etc.
    def _replace_ol_block(m):
        items = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', m.group(0), flags=re.MULTILINE)
        return f'<ol>{items}</ol>'
    html = re.sub(r'(^\d+\. .+$\n?)+', _replace_ol_block, html, flags=re.MULTILINE)

    # Wrap remaining plain-text blocks in <p> tags (skip lines that are already block tags)
    block_tags = re.compile(r'^<(h[1-6]|ul|ol|li|blockquote|pre|div)', re.IGNORECASE)
    lines = html.split('\n')
    result = []
    buffer = []

    def flush_buffer():
        chunk = ' '.join(buffer).strip()
        if chunk:
            result.append(f'<p>{chunk}</p>')
        buffer.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_buffer()
        elif block_tags.match(stripped):
            flush_buffer()
            result.append(stripped)
        else:
            buffer.append(stripped)

    flush_buffer()
    return '\n'.join(result)

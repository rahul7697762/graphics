"""
Blog AI Service
Handles all AI-powered generation via Perplexity (sonar-pro) and OpenAI (GPT-4o / DALL-E 3).
Ported from Node.js: perplexityService.js + openAIService.js
"""

import os
import json
import requests
from typing import Optional


PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PERPLEXITY_BASE_URL = "https://api.perplexity.ai/chat/completions"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _perplexity_call(user_prompt: str, system_msg: str = "You are an expert.", max_tokens: int = 4000) -> str:
    """Make a single call to Perplexity sonar-pro and return the text content."""
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-pro",
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
    Returns: {"topic": str, "keywords": str}
    """
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
    """Return a comma-separated list of SEO keywords for the given topic."""
    prompt = f'Generate relevant keywords for "{topic}" as comma-separated list.'
    return _perplexity_call(prompt, "You are an SEO expert.", max_tokens=500)


def generate_blog_content(
    topic: str,
    keywords: str,
    language: str,
    audience: str,
    style: str,
    length_num: int,
    interlinks: Optional[list] = None,
    max_attempts: int = 3,
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
            [f'- Link to "{lnk["title"]}" ({lnk["link"]})' for lnk in interlinks]
        )
        interlink_instructions = f"""
        MANDATORY INTERLINKING RULES:
        1. You MUST include links to the following articles within the content.
        2. Do NOT list them at the end. Do NOT show the raw URL.
        3. You MUST use relevant keywords or phrases as the anchor text for the link.
        4. The link must flow naturally in the sentence.

        Articles to integrate:
        {links_str}
        """

    while word_count < length_num and current_attempts < max_attempts:
        current_attempts += 1
        continuation = (
            f"Continue strictly from previous text: {blog_text[-100:]}"
            if blog_text
            else "Start from the beginning."
        )

        prompt = f"""
        You are a professional human blogger who writes helpful, experience-driven real estate articles in first person.
        Write an engaging blog for {audience} in {language} on "{topic}".

        Keywords to include: {keywords or "none"}.
        Style: {style}.
        Minimum Words: {length_num}.

        CONTENT REQUIREMENTS:
        - Write in first person, sharing real-experience style insights.
        - Tone: friendly, conversational, easy to understand. Avoid jargon.
        - Structure: Hooking Introduction, 4–6 main sections, Conclusion with CTA.
        - Use Markdown format: ## for main sections, ### for subsections, **bold**, *italic*.

        {interlink_instructions}

        ⚠️ Important:
        - Do not use [1], [2] citation numbers.
        - Insert valid external references as clickable Markdown links if relevant.
        - {continuation}

        Output valid Markdown.
        """

        new_content = _perplexity_call(prompt, "You are an expert content writer.", max_tokens=4000)
        blog_text += "\n\n" + new_content
        word_count = len(blog_text.split())

    return {"blogText": blog_text.strip(), "wordCount": word_count}


def generate_seo_title(blog_text: str, topic: str) -> str:
    """Generate an SEO-optimised title (max 60 chars) from blog content."""
    prompt = (
        f"Based on this blog content, generate the best SEO-friendly title (max 60 characters) "
        f"that is catchy and optimized for search engines:\n{blog_text[:1200]}\n"
        f"Topic: {topic}\nReturn only the title, nothing else."
    )
    try:
        return _perplexity_call(prompt, "You are an expert SEO copywriter.", max_tokens=50).strip()
    except Exception as e:
        print(f"Perplexity SEO title error: {e}")
        return topic


def check_plagiarism(blog_text: str) -> str:
    """Check plagiarism using Perplexity. Returns a human-readable result string."""
    if not blog_text or not blog_text.strip():
        return "Plagiarism check skipped - empty content"

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
    prompt = f'Generate 5-10 relevant SEO keywords for "{topic}" as a comma-separated list.'
    try:
        return _openai_chat_call(prompt, "You are an SEO expert.", max_tokens=100)
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
            [f'- Link to "{lnk["title"]}" ({lnk["link"]})' for lnk in interlinks]
        )
        interlink_instructions = f"""
        MANDATORY INTERLINKING RULES:
        1. You MUST include links to the following articles within the content.
        2. Do NOT list them at the end. Do NOT show the raw URL.
        3. You MUST use relevant keywords or phrases as the anchor text for the link.
        4. The link must flow naturally in the sentence.

        Articles to integrate:
        {links_str}
        """

    prompt = f"""
    You are a professional human blogger who writes helpful, experience-driven articles.
    Write an engaging blog for {audience} in {language} on "{topic}".

    Keywords to include: {keywords or "none"}.
    Style: {style}.
    Minimum Words: {length_num}.

    CONTENT REQUIREMENTS:
    - Write in first person, sharing real-experience style insights.
    - Tone: friendly, conversational, easy to understand. Avoid jargon.
    - Structure: Hooking Introduction, 4–6 main sections, Conclusion with CTA.
    - Use Markdown format: ## for main sections, ### for subsections, **bold**, *italic*.

    {interlink_instructions}

    ⚠️ Important:
    - Do not use [1], [2] citation numbers.
    - Insert valid external references as clickable Markdown links if relevant.
    """

    blog_text = _openai_chat_call(prompt, "You are an expert content writer.", max_tokens=4000)
    return {"blogText": blog_text.strip(), "wordCount": len(blog_text.split())}


def generate_image(topic: str, image_text: str) -> str:
    """Generate a blog header image via DALL-E 3 and return the image URL."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    prompt = (
        f'Create a professional blog header image about: {topic}.\n\n'
        f'VISUAL REQUIREMENTS:\n'
        f'- High-quality, modern design with relevant visual elements\n'
        f'- Blog header format (landscape orientation, 16:9 ratio)\n'
        f'- Clean, professional appearance suitable for publication\n\n'
        f'TEXT OVERLAY REQUIREMENTS:\n'
        f'- Include the exact text: "{image_text}"\n'
        f'- Text must be spelled EXACTLY as written above, character by character\n'
        f'- Place text prominently, readable, and well-positioned on the image\n'
        f'- Use clean, modern typography (sans-serif font recommended)\n\n'
        f'CRITICAL: The text "{image_text}" must appear exactly as written, with perfect spelling and clear visibility.'
    )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": "1792x1024",
        "response_format": "url",
    }
    res = requests.post(OPENAI_IMAGE_URL, headers=headers, json=payload, timeout=120)
    res.raise_for_status()
    return res.json()["data"][0]["url"]


# ─────────────────────────────────────────────────────────────────────────────
# HTML FORMATTER (shared utility)
# ─────────────────────────────────────────────────────────────────────────────

def format_markdown_to_html(text: str) -> str:
    """Convert Markdown blog text to basic HTML."""
    import re
    html = text
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener noreferrer" style="color: #2563eb; text-decoration: underline;">\1</a>',
        html,
    )
    html = re.sub(r'\n{2,}', '</p><p>', html)
    return '<p>' + html + '</p>'

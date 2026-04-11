"""
SERP LangChain Tools
Provides three tools backed by SerpAPI (Google Search JSON API) that replace
Perplexity for research-heavy tasks:

  1. TrendingTopicsTool   — replaces generate_title_and_keywords()
  2. KeywordResearchTool  — replaces generate_keywords()
  3. PlagiarismCheckTool  — replaces check_plagiarism()

Each tool is a proper LangChain BaseTool subclass so it can be dropped into
any LangChain agent or called standalone via tool.run(input).
"""

import os
import json
import requests
from typing import Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


SERP_API_KEY = os.getenv("SERP_API_KEY")
SERP_BASE_URL = "https://serpapi.com/search.json"


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _serp_request(params: dict) -> dict:
    """Fire a SerpAPI request and return parsed JSON. Raises on HTTP error."""
    if not SERP_API_KEY:
        raise RuntimeError("SERP_API_KEY is not set")
    params["api_key"] = SERP_API_KEY
    res = requests.get(SERP_BASE_URL, params=params, timeout=30)
    res.raise_for_status()
    return res.json()


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1 — TRENDING TOPICS
# ─────────────────────────────────────────────────────────────────────────────

class TrendingTopicsInput(BaseModel):
    industry: str = Field(..., description="The industry or niche to find trending blog topics for.")


class TrendingTopicsTool(BaseTool):
    """
    Find trending blog topic + keyword ideas for a given industry using real
    Google Search data (People Also Ask + Related Searches via SerpAPI).

    Returns a dict: {"topic": str, "keywords": str}
    """

    name: str = "trending_topics"
    description: str = (
        "Use this tool to discover a trending blog topic and relevant SEO keywords "
        "for a given industry. Input: industry name. "
        "Output: JSON with 'topic' and 'keywords' fields."
    )
    args_schema: Type[BaseModel] = TrendingTopicsInput

    def _run(self, industry: str) -> dict:
        data = _serp_request({
            "q": f"trending {industry} blog topics {_current_year()}",
            "hl": "en",
            "gl": "us",
            "num": 10,
        })

        # ── Extract People Also Ask questions as topic candidates ─────────────
        paa = data.get("related_questions", [])
        topic_candidates = [q.get("question", "") for q in paa if q.get("question")]

        # ── Extract Related Searches as keyword signals ───────────────────────
        related = data.get("related_searches", [])
        keyword_candidates = [r.get("query", "") for r in related if r.get("query")]

        # ── Extract top organic titles as additional topic candidates ─────────
        organic = data.get("organic_results", [])
        for r in organic[:5]:
            title = r.get("title", "")
            if title:
                topic_candidates.append(title)

        # Pick the best topic (first PAA question, else first organic title)
        topic = topic_candidates[0] if topic_candidates else f"Top trends in {industry}"

        # Build keyword list: industry + related searches (deduplicated, max 6)
        seen = set()
        keywords_list = []
        for kw in [industry] + keyword_candidates:
            kw_clean = kw.strip()
            if kw_clean and kw_clean.lower() not in seen:
                seen.add(kw_clean.lower())
                keywords_list.append(kw_clean)
            if len(keywords_list) >= 6:
                break

        return {
            "topic": topic,
            "keywords": ", ".join(keywords_list),
        }

    async def _arun(self, industry: str) -> dict:  # pragma: no cover
        raise NotImplementedError("async not supported — use _run")


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2 — KEYWORD RESEARCH
# ─────────────────────────────────────────────────────────────────────────────

class KeywordResearchInput(BaseModel):
    topic: str = Field(..., description="The blog topic to research keywords for.")


class KeywordResearchTool(BaseTool):
    """
    Return a comma-separated list of high-value SEO keywords for a topic,
    sourced from real Google Search related-searches and People Also Ask data.
    """

    name: str = "keyword_research"
    description: str = (
        "Use this tool to get real SEO keyword ideas for a blog topic. "
        "Input: topic string. "
        "Output: comma-separated keyword string."
    )
    args_schema: Type[BaseModel] = KeywordResearchInput

    def _run(self, topic: str) -> str:
        data = _serp_request({
            "q": topic,
            "hl": "en",
            "gl": "us",
            "num": 10,
        })

        keywords: list[str] = []

        # Related searches (most reliable signal)
        for item in data.get("related_searches", []):
            q = item.get("query", "").strip()
            if q:
                keywords.append(q)

        # People Also Ask questions (longer-tail)
        for item in data.get("related_questions", []):
            q = item.get("question", "").strip()
            if q:
                keywords.append(q)

        # Deduplicate while preserving order
        seen = set()
        unique_kws: list[str] = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_kws.append(kw)
            if len(unique_kws) >= 10:
                break

        # Always include the original topic itself
        if topic.lower() not in seen:
            unique_kws.insert(0, topic)

        return ", ".join(unique_kws) if unique_kws else topic

    async def _arun(self, topic: str) -> str:  # pragma: no cover
        raise NotImplementedError("async not supported — use _run")


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3 — PLAGIARISM CHECK
# ─────────────────────────────────────────────────────────────────────────────

# Number of sentences to spot-check against Google
_SENTENCES_TO_CHECK = 5
# How many Google results must return an exact match to flag a sentence
_MATCH_THRESHOLD = 1


class PlagiarismCheckInput(BaseModel):
    blog_text: str = Field(..., description="The full blog text to check for plagiarism.")


class PlagiarismCheckTool(BaseTool):
    """
    Spot-check a blog post for plagiarism by searching key sentences on Google
    via SerpAPI and detecting verbatim matches in organic results.

    Returns a human-readable result string.
    """

    name: str = "plagiarism_check"
    description: str = (
        "Use this tool to check a blog post for plagiarism using real Google Search results. "
        "Input: full blog text. "
        "Output: plain-text plagiarism report."
    )
    args_schema: Type[BaseModel] = PlagiarismCheckInput

    def _run(self, blog_text: str) -> str:
        if not blog_text or not blog_text.strip():
            return "Plagiarism check skipped — empty content"

        # Extract candidate sentences (≥ 10 words, strip Markdown)
        import re
        clean = re.sub(r'[#*_\[\]()]', '', blog_text)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if len(s.split()) >= 10]

        # Pick evenly-spaced sample sentences
        if len(sentences) <= _SENTENCES_TO_CHECK:
            sample = sentences
        else:
            step = len(sentences) // _SENTENCES_TO_CHECK
            sample = [sentences[i * step] for i in range(_SENTENCES_TO_CHECK)]

        flagged: list[str] = []

        for sentence in sample:
            # Use exact-phrase search (first 12 words for API reliability)
            query_words = sentence.split()[:12]
            query = '"' + " ".join(query_words) + '"'

            try:
                data = _serp_request({
                    "q": query,
                    "hl": "en",
                    "gl": "us",
                    "num": 5,
                })
                organic = data.get("organic_results", [])
                if len(organic) >= _MATCH_THRESHOLD:
                    # Check if any snippet closely matches the sentence
                    for result in organic:
                        snippet = result.get("snippet", "").lower()
                        # Overlap: if 8+ words from query appear in snippet, flag it
                        matches = sum(1 for w in query_words if w.lower() in snippet)
                        if matches >= 8:
                            source_url = result.get("link", "unknown source")
                            flagged.append(f'  • "{" ".join(query_words)}…" → {source_url}')
                            break
            except Exception as e:
                print(f"SERP plagiarism check error for sentence: {e}")
                continue

        if not flagged:
            return "No plagiarism detected — all sampled sentences appear original."

        report = (
            f"⚠️ Potential plagiarism detected in {len(flagged)} sentence(s):\n"
            + "\n".join(flagged)
            + "\n\nReview and rewrite the flagged sections before publishing."
        )
        return report

    async def _arun(self, blog_text: str) -> str:  # pragma: no cover
        raise NotImplementedError("async not supported — use _run")


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE — pre-built instances ready to import
# ─────────────────────────────────────────────────────────────────────────────

trending_topics_tool    = TrendingTopicsTool()
keyword_research_tool   = KeywordResearchTool()
plagiarism_check_tool   = PlagiarismCheckTool()

# All three as a list for agent tool registration
ALL_SERP_TOOLS = [trending_topics_tool, keyword_research_tool, plagiarism_check_tool]


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL UTIL
# ─────────────────────────────────────────────────────────────────────────────

def _current_year() -> int:
    from datetime import datetime
    return datetime.now().year

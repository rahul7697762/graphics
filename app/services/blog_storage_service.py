"""
Blog Storage Service
Handles Supabase interactions, image upload to Supabase Storage,
credit ledger validation/deduction, and push notification forwarding.
Ported from Node.js: articleController.js + blogController.js
"""

import os
import math
import re
import time
import random
import requests
from typing import Optional

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")          # anon key  (for scoped/user clients)
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service-role key (for admin RPCs)

ADMIN_ID = "0d396440-7d07-407c-89da-9cb93e353347"

# URL of the Node.js API server (used for push notification proxy)
NODE_API_URL = os.getenv("NODE_API_URL", "http://localhost:3001")


# ─────────────────────────────────────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

def get_scoped_supabase(token: str) -> Client:
    """Return a Supabase client scoped to the user's JWT (for RLS enforcement)."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options={"headers": {"Authorization": f"Bearer {token}"}},
    )


def get_admin_supabase() -> Client:
    """Return a Supabase admin client (bypasses RLS — used for credit RPCs)."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
    return create_client(SUPABASE_URL, key)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_table_name(user_id: str, target_table: Optional[str] = None) -> str:
    """
    Determine which Supabase table to use.
    Admin defaults to company_articles; everyone else gets articles.
    Admin can override with target_table='articles'.
    """
    if user_id == ADMIN_ID:
        if target_table == "articles":
            return "articles"
        return "company_articles"
    return "articles"


def generate_slug(text: str) -> str:
    """Convert a title string into a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[\s\W-]+", "-", slug)
    slug = re.sub(r"^-+|-+$", "", slug)
    return slug


def calculate_read_time(word_count: int) -> int:
    """Estimate reading time in minutes (200 wpm average)."""
    return math.ceil(word_count / 200)


# ─────────────────────────────────────────────────────────────────────────────
# CREDIT LEDGER
# ─────────────────────────────────────────────────────────────────────────────

def validate_credits(user_id: str, agent_type: str = "blog", quantity: int = 1) -> dict:
    """
    Check if the user has enough credits.
    Returns {"hasEnough": bool, "creditsNeeded": float, "currentBalance": float, "deficit": float}
    """
    admin_sb = get_admin_supabase()

    # Get pricing
    pricing_res = (
        admin_sb.table("agent_pricing")
        .select("unit_cost")
        .eq("agent_type", agent_type)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if pricing_res.data is None:
        raise RuntimeError(f"No pricing found for agent: {agent_type}")

    credits_needed = quantity * pricing_res.data["unit_cost"]

    # Get balance
    balance_res = (
        admin_sb.table("user_credits")
        .select("balance")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if balance_res.data is None:
        raise RuntimeError("Could not retrieve user credit balance")

    current_balance = balance_res.data["balance"]
    has_enough = current_balance >= credits_needed

    return {
        "hasEnough": has_enough,
        "creditsNeeded": credits_needed,
        "currentBalance": current_balance,
        "deficit": 0 if has_enough else credits_needed - current_balance,
    }


def deduct_credits(
    user_id: str,
    agent_type: str,
    reference_id: str,
    reference_table: str,
    usage_quantity: int,
    metadata: dict,
) -> dict:
    """
    Atomically deduct credits via the PostgreSQL RPC function.
    Returns the RPC result dict with credits_deducted, new_balance, ledger_id.
    """
    admin_sb = get_admin_supabase()
    result = admin_sb.rpc(
        "deduct_credits_with_ledger",
        {
            "p_user_id": user_id,
            "p_agent_type": agent_type,
            "p_reference_id": reference_id,
            "p_reference_table": reference_table,
            "p_usage_quantity": usage_quantity,
            "p_metadata": metadata,
        },
    ).execute()

    if result.data and not result.data.get("success"):
        raise RuntimeError(result.data.get("error", "Credit deduction failed"))

    return result.data


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE STORAGE
# ─────────────────────────────────────────────────────────────────────────────

def upload_image_to_supabase(image_url: str, scoped_supabase: Client) -> str:
    """
    Download image from URL and upload to Supabase Storage 'blog-images' bucket.
    Returns the public URL of the persisted image.
    Falls back to original URL on any error.
    """
    try:
        img_res = requests.get(image_url, timeout=30)
        img_res.raise_for_status()
        file_bytes = img_res.content
        file_name = f"blog-{int(time.time())}-{random.randint(0, 999)}.png"

        scoped_supabase.storage.from_("blog-images").upload(
            file_name,
            file_bytes,
            {"content-type": "image/png", "upsert": "false"},
        )

        public_url_res = scoped_supabase.storage.from_("blog-images").get_public_url(file_name)
        return public_url_res if isinstance(public_url_res, str) else image_url
    except Exception as e:
        print(f"[Blog Storage] Image upload failed, using original URL: {e}")
        return image_url


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE CRUD
# ─────────────────────────────────────────────────────────────────────────────

def save_article(payload: dict, scoped_supabase: Client, table_name: str) -> dict:
    """Insert a new article row and return the saved record."""
    result = (
        scoped_supabase.table(table_name)
        .insert(payload)
        .select("*")
        .single()
        .execute()
    )
    if result.data is None:
        raise RuntimeError("Failed to save article to Supabase")
    return result.data


def get_posts(scoped_supabase: Client, table_name: str, page: int = 1, limit: int = 10, status: Optional[str] = None) -> dict:
    """Fetch paginated posts from the given table."""
    from_ = (page - 1) * limit
    to_ = from_ + limit - 1

    query = (
        scoped_supabase.table(table_name)
        .select("*", count="exact")
        .order("created_at", desc=True)
        .range(from_, to_)
    )
    if status == "published":
        query = query.eq("is_published", True)
    elif status == "draft":
        query = query.eq("is_published", False)

    result = query.execute()
    total = result.count or 0
    return {
        "posts": result.data or [],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": math.ceil(total / limit) if limit else 0,
        },
    }


def get_post_by_id(scoped_supabase: Client, table_name: str, post_id: str) -> dict:
    """Fetch a single post by its UUID."""
    result = (
        scoped_supabase.table(table_name)
        .select("*")
        .eq("id", post_id)
        .single()
        .execute()
    )
    if result.data is None:
        raise LookupError(f"Post {post_id} not found")
    return result.data


def create_post(scoped_supabase: Client, table_name: str, user_id: str, body: dict) -> dict:
    """Manually create a blog post (non-AI-generated CMS use-case)."""
    from datetime import datetime, timezone

    post_data = {
        "user_id": user_id,
        "topic": body.get("title"),
        "slug": body.get("slug"),
        "content": body.get("content"),
        "seo_title": body.get("seo_title"),
        "seo_description": body.get("seo_description"),
        "keywords": body.get("keywords"),
        "is_published": body.get("is_published", False),
        "publish_date": body.get("publish_date"),
        "featured_image": body.get("featured_image"),
        "category": body.get("category"),
        "author_name": body.get("author_name"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = (
        scoped_supabase.table(table_name)
        .insert(post_data)
        .select("*")
        .single()
        .execute()
    )
    if result.data is None:
        raise RuntimeError("Failed to create post")
    return result.data


def update_post(scoped_supabase: Client, table_name: str, post_id: str, updates: dict) -> dict:
    """Update fields on an existing post and return updated record."""
    from datetime import datetime, timezone

    # Strip immutable fields
    for field in ("id", "created_at", "user_id", "notification_settings"):
        updates.pop(field, None)

    if "title" in updates:
        updates["topic"] = updates["title"]

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        scoped_supabase.table(table_name)
        .update(updates)
        .eq("id", post_id)
        .select("*")
        .single()
        .execute()
    )
    if result.data is None:
        raise RuntimeError(f"Failed to update post {post_id}")
    return result.data


def delete_post(scoped_supabase: Client, table_name: str, post_id: str) -> None:
    """Delete a post by ID."""
    scoped_supabase.table(table_name).delete().eq("id", post_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC BLOG READS (no auth)
# ─────────────────────────────────────────────────────────────────────────────

def get_public_blogs(page: int = 1, limit: int = 10, sort: str = "created_at", order: str = "desc") -> dict:
    """Fetch company_articles for public-facing blog pages (no auth required)."""
    admin_sb = get_admin_supabase()
    offset = (page - 1) * limit

    result = (
        admin_sb.table("company_articles")
        .select("*, author:blog_profiles(*)", count="exact")
        .order(sort, desc=(order == "desc"))
        .range(offset, offset + limit - 1)
        .execute()
    )
    count = result.count or 0
    total_pages = math.ceil(count / limit) if limit else 0
    return {
        "articles": result.data or [],
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalArticles": count,
            "limit": limit,
            "hasNextPage": page < total_pages,
            "hasPrevPage": page > 1,
        },
    }


def get_public_blog_by_id_or_slug(identifier: str) -> dict:
    """Fetch a single company article by UUID or slug."""
    import re as _re

    admin_sb = get_admin_supabase()
    uuid_re = _re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", _re.I
    )
    query = admin_sb.table("company_articles").select("*, author:blog_profiles(*)")
    if uuid_re.match(identifier):
        query = query.eq("id", identifier)
    else:
        query = query.eq("slug", identifier)

    result = query.single().execute()
    if result.data is None:
        raise LookupError(f"Article '{identifier}' not found")
    return result.data


# ─────────────────────────────────────────────────────────────────────────────
# PUSH NOTIFICATION (proxied to Node.js pushService)
# ─────────────────────────────────────────────────────────────────────────────

def send_push_notification(title: str, body: str, image_url: Optional[str], slug: Optional[str]) -> None:
    """
    Fire-and-forget push notification by calling the Node.js /api/push/send endpoint.
    Firebase Admin SDK stays in Node.js to avoid duplicate SDK setup.
    Errors are silently logged so they never block the blog generation response.
    """
    try:
        payload = {
            "title": title,
            "body": body,
            "image": image_url,
            "target": "all",
            "data": {"slug": slug or "", "type": "new_blog"},
        }
        requests.post(
            f"{NODE_API_URL}/api/push/send",
            json=payload,
            timeout=10,
        )
    except Exception as e:
        print(f"[Blog] Push notification failed (non-critical): {e}")

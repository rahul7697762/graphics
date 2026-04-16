"""
A/B Test Service for SEO AI Agent Blog Generation Pipeline
===========================================================

Active experiment:
  Name    : content_model_v1
  Control : Perplexity sonar-pro  (variant="A")
  Variant : Perplexity sonar      (variant="B")

Hypothesis:
  Because sonar-pro has deeper reasoning and higher context capacity,
  we believe it produces content closer to the target word count and with
  lower plagiarism-hit rate than the lighter sonar model.
  We'll know this is true when word-count accuracy and plagiarism pass-rate
  differ with ≥95% statistical confidence across ≥200 generations per arm.

Assignment is purely server-side — never exposed in API responses or logs
visible to clients.

Metrics:
  Primary   : word_count_accuracy  (|actual - target| / target, lower is better)
  Secondary : plagiarism_pass_rate (fraction of checks with no plagiarism detected)
  Guardrail : generation_error_rate (must not exceed 5% in either arm)

Sample size:
  Baseline word-count accuracy ≈ 85%, MDE = 10 pp → ~200 samples/arm needed.

Traffic split : 50 / 50
Assignment    : deterministic hash of (user_id + topic) — same input always
               gets same variant so re-runs are consistent.
"""

import hashlib
import os
from typing import Literal

Variant = Literal["A", "B"]

# Flip this to True to force everyone into the control arm (kill-switch).
EXPERIMENT_DISABLED = os.getenv("AB_TEST_DISABLED", "false").lower() == "true"

# Override variant for manual QA: set AB_FORCE_VARIANT=A or =B
_FORCED_VARIANT = os.getenv("AB_FORCE_VARIANT", "").upper()


def assign_variant(topic: str) -> Variant:
    """
    Deterministically assign a variant for the content_model_v1 experiment.
    Assignment is based on topic only — purely server-side, never exposed to clients.

    Returns:
        "A"  → Perplexity sonar-pro  (control)
        "B"  → Perplexity sonar      (treatment — lighter/faster model)
    """
    if EXPERIMENT_DISABLED:
        return "A"

    if _FORCED_VARIANT in ("A", "B"):
        return _FORCED_VARIANT  # type: ignore[return-value]

    seed = f"{topic}:content_model_v1"
    digest = hashlib.md5(seed.encode()).hexdigest()
    # Use the last 8 hex chars as a uint32; even → A, odd → B
    bucket = int(digest[-8:], 16)
    return "B" if bucket % 2 == 1 else "A"


def variant_label(variant: Variant) -> str:
    """Human-readable label for logging."""
    return "perplexity-sonar-pro" if variant == "A" else "perplexity-sonar"

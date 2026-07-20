"""Thin wrapper around the Anthropic SDK.

The `anthropic` package is imported lazily so the tool still runs in a fully
offline "heuristic" mode when the SDK or credentials are absent.
"""

import json
import os
from typing import Optional, Tuple

from .config import ANALYSIS_MAX_TOKENS, GENERATION_MAX_TOKENS, MODEL


def availability() -> Tuple[bool, str]:
    """Return (usable, reason_if_not)."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False, "the 'anthropic' package is not installed (pip install anthropic)"
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return False, "no ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN in the environment"
    return True, ""


def _client():
    import anthropic

    return anthropic.Anthropic()


def analyze_structured(system: str, user: str, schema: dict, model: Optional[str] = None) -> dict:
    """One structured-output call that returns parsed JSON matching `schema`."""
    client = _client()
    resp = client.messages.create(
        model=model or MODEL,
        max_tokens=ANALYSIS_MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": schema},
        },
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return json.loads(text)


def generate_text(system: str, user: str, model: Optional[str] = None,
                  max_tokens: int = GENERATION_MAX_TOKENS) -> str:
    """Stream a long free-form completion and return the concatenated text."""
    client = _client()
    with client.messages.stream(
        model=model or MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")

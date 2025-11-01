"""Utilities to robustly parse JSON-like responses from LLMs.

This aims to handle common formatting issues like Markdown code fences
and stray prose before/after the JSON payload.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def _try_json_loads(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


def parse_llm_json(content: str) -> Dict[str, Any]:
    """Parse a JSON object from an LLM string response.

    Strategy:
    1) Direct json.loads
    2) Extract inside Markdown code fences ```json ... ``` or ``` ... ```
    3) Extract the first JSON object substring using a permissive regex
    4) Fallback to an Unverifiable payload containing the raw content in reasoning
    """
    # 1) Direct parse
    parsed = _try_json_loads(content)
    if parsed is not None:
        return parsed

    # 2) Code fences
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content, re.IGNORECASE)
    if fence_match:
        parsed = _try_json_loads(fence_match.group(1))
        if parsed is not None:
            return parsed

    # 3) First JSON object substring (non-greedy across lines)
    obj_match = re.search(r"(\{[\s\S]*\})", content)
    if obj_match:
        parsed = _try_json_loads(obj_match.group(1))
        if parsed is not None:
            return parsed

    # 4) Fallback
    return {
        "verdict": "Unverifiable",
        "confidence": 0.0,
        "reasoning": content,
        "citations": [],
    }

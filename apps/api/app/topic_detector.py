from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_TOPIC_JUDGE_PROMPT = """\
You are a topic-continuity judge. Given the CURRENT topic summary and a NEW user message, decide:
1. Does the new message belong to the same topic? ("same_topic": true/false)
2. Is it a sub-topic / deeper dive of the current topic? ("is_subtopic": true/false)

Rules:
- "same_topic": true if the message continues, deepens, or directly relates to the current topic
- "is_subtopic": true only when the new message drills deeper into a specific aspect of the current topic (e.g. current="天气" and new="北京的天气")
- "is_subtopic" can only be true when "same_topic" is also true

Respond with ONLY a JSON object on a single line:
{"same_topic": true, "is_subtopic": false, "summary": "brief topic label max 40 chars"}
No markdown, no explanation, no extra text."""

# Regex to extract the first JSON object from a string that may contain preamble/wrapping.
_JSON_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.IGNORECASE | re.DOTALL)
_MD_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


@dataclass
class TopicDecision:
    is_new_topic: bool
    is_subtopic: bool
    summary: str
    confidence: float


def _extract_json(raw: str) -> dict | None:
    """Best-effort JSON extraction from LLM output."""
    # Step 1: strip think tags
    raw = _THINK_RE.sub("", raw).strip()

    # Step 2: try direct parse (ideal case)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 3: extract from markdown code fence
    fence = _MD_FENCE_RE.search(raw)
    if fence:
        try:
            return json.loads(fence.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 4: find first {...} substring
    m = _JSON_RE.search(raw)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


async def decide_topic_llm(
    client: AsyncOpenAI,
    model: str,
    message: str,
    previous_summary: Optional[str],
    force_new_topic: bool = False,
    max_tokens: int = 2048,
) -> TopicDecision:
    """Use LLM to decide whether the message is a new topic."""
    if force_new_topic or not previous_summary:
        summary = await _llm_summarize(client, model, message, max_tokens=max_tokens)
        return TopicDecision(
            is_new_topic=True,
            is_subtopic=False,
            summary=summary,
            confidence=1.0 if force_new_topic else 0.9,
        )

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _TOPIC_JUDGE_PROMPT},
                {
                    "role": "user",
                    "content": f"Current topic: {previous_summary}\n\nNew message: {message}",
                },
            ],
            temperature=0.1,
            max_completion_tokens=max_tokens,
        )
        raw = (completion.choices[0].message.content or "").strip()
        result = _extract_json(raw)

        if result is not None:
            same = result.get("same_topic", False)
            is_subtopic = result.get("is_subtopic", False) if same else False
            summary = result.get("summary", _fallback_summarize(message))[:40]
            return TopicDecision(
                is_new_topic=not same,
                is_subtopic=is_subtopic,
                summary=summary,
                confidence=0.9,
            )

        # JSON extraction completely failed — log and use heuristic fallback
        logger.warning("Could not extract JSON from LLM response: %r", raw[:200])

    except Exception as exc:
        logger.warning("LLM topic detection failed: %s", exc)

    # Heuristic fallback: keyword overlap to avoid always-new-topic trap
    return _heuristic_fallback(message, previous_summary)


def _heuristic_fallback(message: str, previous_summary: str) -> TopicDecision:
    """Keyword-overlap heuristic when LLM fails."""
    current_terms = set(_tokenize(message))
    previous_terms = set(_tokenize(previous_summary))
    overlap = len(current_terms & previous_terms)
    if overlap > 0:
        return TopicDecision(
            is_new_topic=False,
            is_subtopic=False,
            summary=_fallback_summarize(message),
            confidence=0.5,
        )
    return TopicDecision(
        is_new_topic=True,
        is_subtopic=False,
        summary=_fallback_summarize(message),
        confidence=0.5,
    )


async def _llm_summarize(client: AsyncOpenAI, model: str, message: str, max_tokens: int = 2048) -> str:
    """Get a short topic summary from LLM."""
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the user's message into a very brief topic label (max 40 chars, same language as user). Reply with ONLY the summary text, nothing else.",
                },
                {"role": "user", "content": message},
            ],
            temperature=0.1,
            max_completion_tokens=max_tokens,
        )
        raw = (completion.choices[0].message.content or "").strip()
        raw = _THINK_RE.sub("", raw).strip()
        return raw[:40] if raw else _fallback_summarize(message)
    except Exception:
        return _fallback_summarize(message)


def _fallback_summarize(text: str) -> str:
    compact = " ".join(text.strip().split())
    return compact[:40] if compact else "empty-topic"


def _tokenize(text: str) -> list[str]:
    """Tokenise for heuristic overlap.  Handles both space-delimited (Latin) and
    CJK text (where words are not separated by spaces) by emitting individual
    CJK characters as well as space-split tokens."""
    import unicodedata
    tokens: list[str] = []
    # Space-split tokens (works for Latin / mixed text)
    for part in text.replace(",", " ").replace(".", " ").split():
        if len(part) > 1:
            tokens.append(part.lower())
    # Individual CJK characters (covers Chinese, Japanese, Korean)
    for ch in text:
        cat = unicodedata.category(ch)
        # Lo = Letter, other — covers most CJK ideographs
        if cat == "Lo" and unicodedata.name(ch, "").startswith(("CJK", "HANGUL", "HIRAGANA", "KATAKANA")):
            tokens.append(ch)
    return tokens


# Keep synchronous version as fallback
def decide_topic(message: str, previous_summary: Optional[str], force_new_topic: bool = False) -> TopicDecision:
    """Synchronous heuristic fallback — prefer decide_topic_llm."""
    if force_new_topic:
        return TopicDecision(is_new_topic=True, is_subtopic=False, summary=_fallback_summarize(message), confidence=1.0)
    if not previous_summary:
        return TopicDecision(is_new_topic=True, is_subtopic=False, summary=_fallback_summarize(message), confidence=0.9)
    return _heuristic_fallback(message, previous_summary)

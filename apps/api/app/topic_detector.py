from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TopicDecision:
    is_new_topic: bool
    summary: str
    confidence: float


def decide_topic(message: str, previous_summary: Optional[str], force_new_topic: bool = False) -> TopicDecision:
    if force_new_topic:
        return TopicDecision(is_new_topic=True, summary=_summarize(message), confidence=1.0)

    if not previous_summary:
        return TopicDecision(is_new_topic=True, summary=_summarize(message), confidence=0.9)

    # High-sensitivity demo heuristic: short keyword overlap means a new node.
    current_terms = set(_tokenize(message))
    previous_terms = set(_tokenize(previous_summary))
    overlap = len(current_terms & previous_terms)
    is_new = overlap == 0
    confidence = 0.82 if is_new else 0.63
    return TopicDecision(is_new_topic=is_new, summary=_summarize(message), confidence=confidence)


def _summarize(text: str) -> str:
    compact = " ".join(text.strip().split())
    return compact[:28] if compact else "empty-topic"


def _tokenize(text: str) -> list[str]:
    return [part.lower() for part in text.replace(",", " ").replace(".", " ").split() if len(part) > 1]

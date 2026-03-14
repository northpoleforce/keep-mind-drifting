from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re

from openai import AsyncOpenAI

from .config import Settings
from .models import ContextItem


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMGateway(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        session_id: str,
        user_message: str,
        context_items: list[ContextItem],
    ) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> dict:
        raise NotImplementedError


class OpenAICompatibleGateway(LLMGateway):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    async def generate(
        self,
        *,
        session_id: str,
        user_message: str,
        context_items: list[ContextItem],
    ) -> LLMResult:
        context_block = "\n".join(f"- ({item.source}:{item.score:.3f}) {item.text}" for item in context_items)
        user_payload = user_message
        if context_block:
            user_payload = f"历史上下文:\n{context_block}\n\n当前用户输入:\n{user_message}"

        request_payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": self.settings.llm_system_prompt},
                {"role": "user", "content": user_payload},
            ],
            "temperature": self.settings.llm_temperature,
            "max_completion_tokens": self.settings.llm_max_completion_tokens,
        }
        if self.settings.llm_use_prompt_cache_key:
            request_payload["prompt_cache_key"] = session_id

        completion = await self.client.chat.completions.create(**request_payload)
        raw_text = (completion.choices[0].message.content or "").strip()
        text = self._sanitize_output(raw_text)
        usage = completion.usage
        return LLMResult(
            text=text,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )

    async def healthcheck(self) -> dict:
        completion = await self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[{"role": "user", "content": "Reply exactly: pong"}],
            temperature=max(0.1, min(float(self.settings.llm_temperature), 1.0)),
            max_completion_tokens=16,
        )
        sample = (completion.choices[0].message.content or "").strip()
        return {
            "ok": True,
            "provider": self.settings.llm_provider,
            "base_url": self.settings.llm_base_url,
            "model": self.settings.llm_model,
            "sample": self._sanitize_output(sample)[:60],
        }

    def _sanitize_output(self, text: str) -> str:
        if not self.settings.llm_strip_think_tags:
            return text
        cleaned = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
        return cleaned.strip()


def build_llm_gateway(settings: Settings) -> LLMGateway:
    provider = settings.llm_provider.strip().lower()
    if provider in {"openai_compatible", "openai-compatible", "kimi", "openai", "minimax"}:
        return OpenAICompatibleGateway(settings)
    raise ValueError(f"Unsupported llm provider: {settings.llm_provider}")

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")

    evermemos_base_url: Optional[str] = Field(default=None, alias="EVERMEMOS_BASE_URL")
    evermemos_api_key: str = Field(default="demo-key", alias="EVERMEMOS_API_KEY")
    evermemos_sender_name: str = Field(default="Evermind Demo", alias="EVERMEMOS_SENDER_NAME")
    evermemos_topic_sender_name: str = Field(
        default="Evermind Topic Detector", alias="EVERMEMOS_TOPIC_SENDER_NAME"
    )
    evermemos_timeout_seconds: float = Field(default=10.0, alias="EVERMEMOS_TIMEOUT_SECONDS")
    evermemos_max_retries: int = Field(default=2, alias="EVERMEMOS_MAX_RETRIES")
    evermemos_consistency_retries: int = Field(default=3, alias="EVERMEMOS_CONSISTENCY_RETRIES")
    evermemos_consistency_delay_ms: int = Field(default=600, alias="EVERMEMOS_CONSISTENCY_DELAY_MS")

    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="demo-key", alias="LLM_API_KEY")
    llm_model: str = Field(default="kimi-k2-turbo-preview", alias="LLM_MODEL")
    llm_provider: str = Field(default="openai_compatible", alias="LLM_PROVIDER")
    llm_temperature: float = Field(default=0.6, alias="LLM_TEMPERATURE")
    llm_max_completion_tokens: int = Field(default=512, alias="LLM_MAX_COMPLETION_TOKENS")
    llm_use_prompt_cache_key: bool = Field(default=False, alias="LLM_USE_PROMPT_CACHE_KEY")
    llm_strip_think_tags: bool = Field(default=True, alias="LLM_STRIP_THINK_TAGS")
    llm_system_prompt: str = Field(
        default="你是 Evermind 的 AI 助手。请基于上下文给出清晰、可执行、简洁的回答。",
        alias="LLM_SYSTEM_PROMPT",
    )

    retrieval_cache_weight: float = Field(default=0.6, alias="RETRIEVAL_CACHE_WEIGHT")
    retrieval_memory_weight: float = Field(default=0.4, alias="RETRIEVAL_MEMORY_WEIGHT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

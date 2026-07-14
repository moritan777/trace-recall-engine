"""Factory for Trace extractor selection from CLI configuration."""

from __future__ import annotations

from typing import Any, Callable

from .base import TraceExtractor
from .fallback import FallbackTraceExtractor
from .llm import LLMTraceExtractor
from .local_rule import LocalRuleTraceExtractor


def create_extractor(args: Any, chat_client: Callable[..., str] | None = None, normalize_base_url: Callable[[str], str] | None = None) -> TraceExtractor:
    extractor_name = getattr(args, "extractor", "llm")
    if extractor_name == "fallback":
        return FallbackTraceExtractor()
    if extractor_name == "local-rule":
        return LocalRuleTraceExtractor(debug=getattr(args, "debug_extractor", False), enable_mixed_script_promotion=getattr(args, "enable_mixed_script_promotion", False))
    if extractor_name == "llm":
        extractor_model = getattr(args, "extractor_model", "") or getattr(args, "model", "local-model")
        return LLMTraceExtractor(
            getattr(args, "base_url", ""),
            getattr(args, "api_key", ""),
            extractor_model,
            getattr(args, "timeout", 12.0),
            debug=getattr(args, "debug_extractor", False),
            chat_client=chat_client,
            normalize_base_url=normalize_base_url,
        )
    raise ValueError(f"Unknown extractor: {extractor_name}")

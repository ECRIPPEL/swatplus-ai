"""LLM gateway — provider-agnostic interface for prompt completion & streaming."""

from __future__ import annotations

from swatplus_ai.llm.backends.api_key import AnthropicBackend, OpenAIBackend
from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.backends.oauth import AnthropicOAuthBackend, OpenAIOAuthBackend
from swatplus_ai.llm.interface import (
    AuthError,
    LLMBackend,
    LLMError,
    LLMResponse,
    Message,
    RateLimitError,
    Role,
    split_system,
)
from swatplus_ai.llm.tokens import KeyringTokenStore, MemoryTokenStore, TokenStore

__all__ = [
    "AnthropicBackend",
    "AnthropicOAuthBackend",
    "AuthError",
    "KeyringTokenStore",
    "LLMBackend",
    "LLMError",
    "LLMResponse",
    "MemoryTokenStore",
    "Message",
    "MockBackend",
    "OpenAIBackend",
    "OpenAIOAuthBackend",
    "RateLimitError",
    "Role",
    "TokenStore",
    "split_system",
]

"""LLM Assistant v2.0.0 — модульная версия."""

from .app import LLMAssistant
from .common import DEFAULT_MODEL_NAME

__all__ = ["LLMAssistant", "DEFAULT_MODEL_NAME"]

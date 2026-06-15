"""LLM Assistant v1.01 — модульная версия."""

from .app import LLMAssistant
from .common import DEFAULT_MODEL_NAME

__all__ = ["LLMAssistant", "DEFAULT_MODEL_NAME"]

"""
LLM Assistant v1.01 — Live UI Localization
════════════════════════════════════════════════════════
Новое в v6:
  • Умный поиск — 4 источника с авто-переключением при затыке:
      GitHub API  → реальный код из репозиториев
      Stack Overflow API → решения ошибок с кодом
      Tavily API  → документация и статьи (AI-ready текст)
      DuckDuckGo  → бесплатный fallback без ключа
  • Красивый диалог «🔑 Источники поиска» — настройка одним окном
  • Умный роутинг: по ключевым словам выбирает лучший источник
  • Индикатор источника в строке поиска (цветные иконки)
  • Авто-переключение при ошибке / пустом ответе / rate-limit
  • API ключи сохраняются в сессии
  • Все возможности v5 сохранены
════════════════════════════════════════════════════════
Зависимости:
  pip install requests python-dotenv beautifulsoup4 duckduckgo-search tkinterdnd2
  Tavily (опционально): pip install tavily-python
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.simpledialog as simpledialog
import threading
import subprocess
import shutil
import socket
import ipaddress
import requests
import json
import os
import sys
import zipfile
import tempfile
import time
import re
import shlex
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    DDGS = None
    HAS_DDGS = False

try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    TavilyClient = None
    HAS_TAVILY = False

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    TkinterDnD = None
    DND_FILES = None
    HAS_DND = False

load_dotenv()

DEFAULT_MODEL_NAME = "qwen/qwen3-coder-30b"

DEFAULT_LANGUAGE_MODE = "English + Русский"
LANGUAGE_PROFILES = {
    "English + Русский": {
        "button": "🌐 EN + RU",
        "color": "#0d6efd",
        "ui": "bi",
    },
    "Русский": {
        "button": "🌐 РУССКИЙ",
        "color": "#198754",
        "ui": "ru",
    },
    "English": {
        "button": "🌐 ENGLISH",
        "color": "#6f42c1",
        "ui": "en",
    },
    "Авто": {
        "button": "🌐 AUTO",
        "color": "#495057",
        "ui": "auto",
    },
}

SERVER_CONFIGS = {
    "LM Studio": {
        "url": "http://localhost:1234/v1",
        "start_mode": "lms",
        "button": "▶ LM STUDIO",
        "color": "#20a464",
    },
    "Ollama": {
        "url": "http://localhost:11434/v1",
        "start_mode": "ollama",
        "button": "▶ OLLAMA",
        "color": "#6f42c1",
    },
    "llama.cpp": {
        "url": "http://localhost:8080/v1",
        "start_mode": "llama_cpp",
        "button": "⚙ LLAMA.CPP",
        "color": "#b7791f",
    },
    "Jan": {
        "url": "http://localhost:1337/v1",
        "start_mode": "jan",
        "button": "▶ JAN API",
        "color": "#0f8b8d",
    },
}

SERVERS = {
    name: str(config["url"])
    for name, config in SERVER_CONFIGS.items()
}
MAX_CONTEXT_TOKENS = 262144
CONTEXT_BUDGET     = 131072
DEFAULT_MAX_TOKENS = 8192

SESSION_DIR  = Path.home() / ".llm_assistant" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SESSION = "default"

EXT_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c",
    ".java": "java", ".cs": "csharp", ".rb": "ruby",
    ".sh": "bash", ".md": "markdown", ".json": "json",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".html": "html", ".css": "css", ".sql": "sql",
    ".txt": "text", ".cfg": "ini", ".ini": "ini",
}

TEMPLATES = {
    "💬 Объясни код":    "Объясни этот код подробно, шаг за шагом:\n\n",
    "🔧 Рефакторинг":   "Сделай рефакторинг кода: улучши читаемость, производительность, следуй PEP8:\n\n",
    "🧪 Написать тесты": "Напиши полный набор unit-тестов (pytest) для этого кода:\n\n",
    "🐛 Найти баги":     "Найди все баги, уязвимости и проблемы в этом коде. Исправь их:\n\n",
    "📝 Документация":   "Напиши полную документацию (docstrings, README-секцию) для этого кода:\n\n",
    "⚡ Оптимизировать": "Оптимизируй этот код по скорости и памяти. Объясни каждое изменение:\n\n",
    "🌐 Веб-анализ":     "Проанализируй содержимое этой веб-страницы и выдели ключевую информацию:\n\n",
    "🔍 Поиск-анализ":   "На основе результатов поиска дай развёрнутый ответ с примерами кода:\n\n",
}

SEARCH_SOURCES = {
    "github":        {"name": "GitHub",         "icon": "🐙", "color": "#238636", "needs_key": False},
    "stackoverflow": {"name": "Stack Overflow",  "icon": "🟠", "color": "#f48024", "needs_key": False},
    "tavily":        {"name": "Tavily",          "icon": "🔷", "color": "#2563eb", "needs_key": True},
    "duckduckgo":    {"name": "DuckDuckGo",      "icon": "🦆", "color": "#de5833", "needs_key": False},
}

SOURCE_ROUTING = {
    "github":        ["github", "репозиторий", "repo", "library", "библиотека",
                      "пример кода", "example", "implementation", "open source"],
    "stackoverflow": ["ошибка", "error", "exception", "traceback", "не работает",
                      "почему", "why", "fix", "исправить", "баг", "bug"],
    "tavily":        ["документация", "docs", "tutorial", "гайд", "guide",
                      "установить", "install", "настройка", "configure"],
}

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime

@dataclass
class WebResult:
    title:     str
    url:       str
    snippet:   str
    full_text: str    = ""
    fetched:   bool   = False
    source:    str    = "duckduckgo"


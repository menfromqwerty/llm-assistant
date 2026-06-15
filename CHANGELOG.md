# Changelog

## v1.01 — 2026-06-15

### Added
- Live UI localization: English, Russian, bilingual and Windows-auto modes
- Language switching without restart via 🌐 LANGUAGE button
- Session persistence for interface language
- GitHub community files: CI, Dependabot, Issue templates

### Security
- Safe ZIP extraction without `extractall` — path traversal and ZIP bomb protection
- API keys excluded from session files
- Migration of old sessions removes stored `api_keys`
- SSRF protection in web page loader
- Custom LLM server URL validated before use
- Removed `shell=True` from all subprocess calls
- Prompt injection protection in system prompt

### Fixed
- API source test no longer reads destroyed Tkinter widgets
- Correct environment variable names for API keys

---

## v1.00 — 2026-06-14

### Core features
- Local AI assistant for embedded development (STM32, ESP32, AVR, Atmel)
- Streaming responses from LM Studio, Ollama, llama.cpp, Jan
- Default model: `qwen/qwen3-coder-30b` (262K context window)
- Smart file context: loads project files with token budget management
- 4-source web search: GitHub, Stack Overflow, Tavily, DuckDuckGo
- Auto-routing and auto-fallback between search sources
- Code Viewer with click-to-extract from chat
- Drag-and-drop files and ZIP into input field
- Session save/restore with chat history and project files
- Model switcher with profiles (temperature, max_tokens, /think)
- Modular architecture: 12 independent mixins + common constants
- Input normalization: tabs to spaces, trailing whitespace cleanup
- Token counter across chat, files and web pages
- Smart layout presets: Code / Read / Standard

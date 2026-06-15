# 🔒 LLM Assistant v1.01

> **AI for hardware development — your code never leaves your machine.**

Local AI assistant for embedded developers working with STM32, ESP32, AVR, Atmel and other microcontrollers. Runs fully offline via LM Studio, Ollama or llama.cpp. No cloud, no leaks, no subscriptions.

---

## Why local AI for embedded development?

When you develop firmware for a commercial device, your source code, schematics, proprietary protocols and register maps are confidential. Sending them to ChatGPT, Copilot or any cloud AI means they leave your machine — permanently.

**LLM Assistant keeps everything local:**

- ✅ Source code stays on your machine
- ✅ Datasheets and register maps never uploaded anywhere
- ✅ Works without internet connection
- ✅ No subscription, no usage limits, no API costs
- ✅ Safe for NDA projects and commercial firmware

---

## Typical tasks

- Analyze HAL code for STM32 and generate peripheral drivers
- Work with ESP32, AVR, Atmel register maps without pasting into a browser
- Refactor and debug firmware code
- Explain datasheet sections and register descriptions
- Write unit tests for embedded code
- Search GitHub and Stack Overflow for real code examples

---

## Features

**🧠 Model switching**
Switch between local models (Qwen3-Coder-30B, DeepSeek-R1, Llama 3.3) and cloud APIs (Groq free tier) in one click. Default is always `qwen/qwen3-coder-30b`.

**📁 Project context**
Load entire project folders, ZIP archives or individual files. Smart chunking sends only relevant files based on your query — fits within the 262K token context window of Qwen3-Coder-30B.

**🌐 Web search (4 sources)**
- 🐙 GitHub — real code from repositories
- 🟠 Stack Overflow — solutions with code
- 🔷 Tavily — documentation and guides (AI-ready text)
- 🦆 DuckDuckGo — free fallback, no key needed

Auto-routing picks the best source based on your query keywords. Falls back automatically if a source is unavailable.

**⚡ Code Viewer**
Click any code block in chat → opens in Code Viewer. Extract all code blocks from a response to a `.py` file in one click.

**💾 Sessions**
Sessions are saved automatically on close to `~/.llm_assistant/sessions/`. Restores chat history, loaded files, model and server settings. Multiple named sessions supported.

**🌐 Interface language**
Switch between English, Russian, bilingual and Windows-auto modes instantly — no restart needed.

**🔧 Input tools**
- Drag-and-drop `.py`, `.c`, `.h` files into the input field → inserted as code blocks
- Drop a `.zip` → auto-extracted into the project
- Normalize indentation (tabs → 4 spaces, trailing whitespace removed)
- Right-click menu: insert file, insert all project files, trim to N tokens

---

## Supported local servers

| Server | Default URL | Notes |
|--------|-------------|-------|
| LM Studio | `localhost:1234` | Recommended for beginners |
| Ollama | `localhost:11434` | Good for Linux/Mac |
| llama.cpp | `localhost:8080` | Lowest resource usage |
| Jan | `localhost:1337` | GUI alternative |
| Custom URL | any | Any OpenAI-compatible API |

---

## Recommended model

**Qwen3-Coder-30B** (default) — best balance of speed and code quality for local inference.

| Quantization | Size | VRAM | Notes |
|---|---|---|---|
| Q4_K_M | ~18 GB | 20 GB | Recommended |
| Q5_K_M | ~22 GB | 24 GB | Better quality |
| Q8_0 | ~32 GB | 36 GB | Near-original |

For systems with less VRAM: DeepSeek-R1-7B or Llama-3.2-8B via Ollama.

---

## Quick start

```powershell
git clone https://github.com/YOUR_USERNAME/llm-assistant.git
cd llm-assistant
pip install -r requirements.txt
python main.py
```

**Optional dependencies:**
```powershell
pip install -r requirements-optional.txt
```

1. Start LM Studio and load `qwen/qwen3-coder-30b`
2. Run `python main.py`
3. The app connects automatically

---

## API keys (optional)

All search sources work without API keys. Keys increase rate limits:

| Source | Without key | With key | Get key |
|--------|------------|---------|---------|
| GitHub | 30 req/min | 5000 req/min | [github.com/settings/tokens](https://github.com/settings/tokens) |
| Stack Overflow | 300 req/day | 10 000 req/day | [stackapps.com](https://stackapps.com/apps/oauth/register) |
| Tavily | ❌ required | 1000 req/month free | [app.tavily.com](https://app.tavily.com/sign-up) |

Copy `.env.example` to `.env` and insert your values. The file is in `.gitignore` — never committed.

---

## Project structure

```
llm_assistant/
├── app.py              — main class assembled from mixins
├── common.py           — constants, dataclasses, shared imports
├── ui.py               — toolbar, menu, chat panel, layout
├── llm_client.py       — streaming requests to LLM server
├── web_search.py       — 4-source search with auto-fallback
├── file_manager.py     — files, ZIP, folder loading
├── model_manager.py    — model switcher and profiles
├── server_manager.py   — server connections and llama.cpp launch
├── sessions.py         — save/load/list sessions
├── context_manager.py  — smart file chunking, token budget
├── input_tools.py      — drag-and-drop, normalize, insert
├── language_manager.py — EN/RU/bilingual UI localization
└── utilities.py        — shared helpers
```

---

## Run tests

```powershell
python -m compileall llm_assistant
pytest -q
```

---

## Security

- API keys are never stored in session files
- ZIP extraction is protected against path traversal and ZIP bombs
- SSRF protection in the web page loader
- Custom LLM server URL is validated before use
- No `shell=True` in subprocess calls

See [SECURITY.md](SECURITY.md) and [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md).

---

## License

MIT — see [LICENSE](LICENSE).

---

## Author

Built for embedded developers who need AI assistance without cloud exposure.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

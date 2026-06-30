from llm_assistant.app import LLMAssistant


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class AutoFitDummy:
    _compact_tokens = staticmethod(LLMAssistant._compact_tokens)
    _effective_context_window = LLMAssistant._effective_context_window
    _effective_input_budget = LLMAssistant._effective_input_budget
    _auto_fit_context_for_prompt = LLMAssistant._auto_fit_context_for_prompt
    _tok = staticmethod(LLMAssistant._tok)

    def __init__(self):
        self._context_presets = (4096, 8192, 16384, 32768, 65536)
        self._context_window_var = Var(8192)
        self._max_tokens_var = Var(4096)
        self._file_context_budget_var = Var(32768)

    def _context_token_breakdown(self):
        return {"chat": 4000, "files": 5000, "web": 0, "total": 9000}

    def _on_generation_limits_changed(self):
        pass


def test_compact_token_labels():
    assert LLMAssistant._compact_tokens(8192) == "8K"
    assert LLMAssistant._compact_tokens(23552) == "23K"
    assert LLMAssistant._compact_tokens(512) == "512"


def test_model_name_matching_accepts_short_and_full_ids():
    match = LLMAssistant._model_name_matches
    assert match("qwen/qwen2.5-coder-14b", "qwen2.5-coder-14b")
    assert match("qwen2.5-coder-14b", "qwen2.5-coder-14b")
    assert not match("qwen2.5-coder-7b", "qwen2.5-coder-14b")


def test_auto_fit_chooses_larger_context_for_prompt():
    app = AutoFitDummy()
    target = app._auto_fit_context_for_prompt("x" * 8000)
    assert target == 32768
    assert app._context_window_var.get() == 32768

class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.content = b"{}"
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_lmstudio_context_inspection(monkeypatch):
    payload = {
        "models": [
            {
                "key": "qwen/qwen2.5-coder-14b",
                "display_name": "Qwen 2.5 Coder 14B",
                "max_context_length": 131072,
                "loaded_instances": [
                    {
                        "id": "qwen2.5-coder-14b",
                        "config": {"context_length": 8192},
                    }
                ],
            }
        ]
    }

    import llm_assistant.server_manager as module
    monkeypatch.setattr(module.requests, "get", lambda *a, **k: FakeResponse(payload))

    app = LLMAssistant.__new__(LLMAssistant)
    info = app._inspect_lmstudio_context(
        "qwen2.5-coder-14b", "http://localhost:1234/v1"
    )
    assert info["loaded"] == 8192
    assert info["maximum"] == 131072
    assert info["model_key"] == "qwen/qwen2.5-coder-14b"

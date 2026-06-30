from unittest.mock import patch

from llm_assistant.sessions import SessionMixin


class Var:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Widget:
    def delete(self, *args):
        pass
    def insert(self, *args):
        pass


class Status:
    def config(self, **kwargs):
        self.kwargs = kwargs


class Dummy(SessionMixin):
    def __init__(self):
        self.is_loading = False
        self.root = object()
        self._session_name = "old"
        self._server_var = Var("Ollama")
        self._server_url = "http://localhost:11434/v1"
        self._model_name = "qwen3:4b"
        self._context_mode_var = Var("selected")
        self._file_context_budget_var = Var(64000)
        self._context_warning_shown = True
        self.chat_history = ["message"]
        self.loaded_files = {"a.py": "a.py"}
        self._file_context_selected = {"a.py": True}
        self._file_token_cache = {"a.py": (1, 2)}
        self._file_list_names = ["a.py"]
        self.current_project = "project"
        self.web_results = ["web"]
        self.input_text = Widget()
        self._search_entry = Widget()
        self._url_entry = Widget()
        self._status = Status()
        self.saved = []
        self.messages = []

    def _save_session(self, name, silent=False):
        self.saved.append(name)
        return True
    def _clear_chat_context(self):
        self.chat_history.clear()
    def _refresh_files_list(self):
        pass
    def _clear_web_context(self):
        self.web_results.clear()
    def _clear_code_viewer(self):
        pass
    def _update_model_ui(self):
        pass
    def _update_session_ui(self):
        pass
    def _update_file_tokens(self):
        pass
    def _update_ctx_label(self):
        pass
    def _add_msg(self, role, content):
        self.messages.append((role, content))


def test_new_session_keeps_ollama_model():
    app = Dummy()
    with patch("llm_assistant.sessions.simpledialog.askstring", return_value="clean"):
        app._new_session()

    assert app._session_name == "clean"
    assert app._server_var.get() == "Ollama"
    assert app._model_name == "qwen3:4b"
    assert app.chat_history == []
    assert app.loaded_files == {}
    assert app.web_results == []
    assert app.current_project is None
    assert app._context_mode_var.get() == "auto"
    assert app._file_context_budget_var.get() == 32768
    assert app.saved == ["old", "clean"]


if __name__ == "__main__":
    test_new_session_keeps_ollama_model()
    print("SESSION_RESET_TEST_OK")

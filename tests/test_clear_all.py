from unittest.mock import patch

from llm_assistant.sessions import SessionMixin


class Entry:
    def __init__(self, value=""):
        self.value = value

    def delete(self, *_args):
        self.value = ""

    def insert(self, _index, value):
        self.value = value


class TextBox:
    def __init__(self, value=""):
        self.value = value
        self.state = None

    def config(self, **kwargs):
        self.state = kwargs.get("state", self.state)

    def delete(self, *_args):
        self.value = ""


class Label:
    def __init__(self, text=""):
        self.text = text

    def config(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]


class ListBox:
    def __init__(self):
        self.cleared = False

    def delete(self, *_args):
        self.cleared = True


class Dummy(SessionMixin):
    def __init__(self):
        self.is_loading = False
        self.root = object()
        self._session_name = "work"
        self.chat_history = ["user", "assistant"]
        self.chat_text = TextBox("visible chat")
        self.web_results = ["result"]
        self._web_lb = ListBox()
        self._web_text = TextBox("page text")
        self._web_tok_label = Label("100 tokens")
        self._search_entry = Entry("query")
        self._url_entry = Entry("https://example.com")
        self._src_status = Label("found 5")
        self.input_text = TextBox("draft must stay")
        self.loaded_files = {"main.py": "main.py"}
        self._status = Label()
        self._stream_buffer = "partial"
        self._in_code_block = True
        self._current_code_tag = "tag"
        self._context_warning_shown = True
        self.saved = []
        self.ctx_updates = 0

    def _ui_language_code(self):
        return "ru"

    def _tr(self, key):
        assert key == "url_placeholder"
        return "URL PLACEHOLDER"

    def _save_session(self, name, silent=False):
        self.saved.append((name, silent))
        return True

    def _update_ctx_label(self):
        self.ctx_updates += 1


def test_clear_messages_and_searches_preserves_files_and_draft():
    app = Dummy()
    with patch("llm_assistant.sessions.messagebox.askyesno", return_value=True):
        app._clear_messages_and_searches()

    assert app.chat_history == []
    assert app.chat_text.value == ""
    assert app.web_results == []
    assert app._web_lb.cleared is True
    assert app._web_text.value == ""
    assert app._web_tok_label.text == ""
    assert app._search_entry.value == ""
    assert app._url_entry.value == "URL PLACEHOLDER"
    assert app._src_status.text == ""
    assert app.loaded_files == {"main.py": "main.py"}
    assert app.input_text.value == "draft must stay"
    assert app._stream_buffer == ""
    assert app._in_code_block is False
    assert app._current_code_tag is None
    assert app._context_warning_shown is False
    assert app.saved == [("work", True)]
    assert app.ctx_updates == 1


def test_clear_is_cancelled_without_confirmation():
    app = Dummy()
    with patch("llm_assistant.sessions.messagebox.askyesno", return_value=False):
        app._clear_messages_and_searches()

    assert app.chat_history == ["user", "assistant"]
    assert app.web_results == ["result"]
    assert app.saved == []

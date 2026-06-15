import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from llm_assistant.file_manager import FileManagerMixin
from llm_assistant.sessions import SessionMixin
from llm_assistant.web_search import WebSearchMixin

class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

class ZipDummy(FileManagerMixin):
    pass

class SessionDummy(SessionMixin):
    def __init__(self):
        self._session_name = "test"
        self._model_name = "qwen3:4b"
        self._server_var = Var("Ollama")
        self._server_url = "http://localhost:11434/v1"
        self._server_model_selection = {"Ollama": "qwen3:4b"}
        self._llama_cpp_settings = {}
        self._max_tokens_var = Var(2048)
        self._temperature_var = Var(0.3)
        self._think_var = Var(False)
        self._language_var = Var("English + Русский")
        self._search_source_var = Var("auto")
        self._context_mode_var = Var("auto")
        self._file_context_budget_var = Var(32768)
        self._file_context_selected = {}
        self._api_keys = {"github": "SECRET_SHOULD_NOT_BE_SAVED"}
        self.chat_history = []
        self.loaded_files = {}
        self.current_project = None
        self.web_results = []

    def _context_token_breakdown(self):
        return {"total": 0, "chat": 0, "files": 0, "web": 0}

    def _update_session_ui(self):
        pass

def test_zip_slip_is_blocked():
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        archive_path = base / "bad.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("../escape.py", "print('bad')")

        destination = base / "extract"
        destination.mkdir()
        app = ZipDummy()
        with zipfile.ZipFile(archive_path, "r") as archive:
            try:
                app._safe_extract_zip(archive, destination)
            except ValueError:
                pass
            else:
                raise AssertionError("Zip Slip archive was accepted")
        assert not (base / "escape.py").exists()

def test_safe_zip_filters_binary_files():
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        archive_path = base / "safe.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("src/main.py", "print('ok')")
            archive.writestr("bin/tool.exe", b"MZ")

        destination = base / "extract"
        destination.mkdir()
        app = ZipDummy()
        with zipfile.ZipFile(archive_path, "r") as archive:
            files = app._safe_extract_zip(archive, destination)
        assert [path.relative_to(destination).as_posix() for path in files] == [
            "src/main.py"
        ]
        assert not (destination / "bin/tool.exe").exists()

def test_api_keys_are_not_written_to_session():
    with TemporaryDirectory() as tmp:
        app = SessionDummy()
        with patch("llm_assistant.sessions.SESSION_DIR", Path(tmp)):
            assert app._save_session("test", silent=True)
            data = json.loads((Path(tmp) / "test.json").read_text(encoding="utf-8"))
        assert "api_keys" not in data
        assert "SECRET_SHOULD_NOT_BE_SAVED" not in json.dumps(data)
        assert data["language_mode"] == "English + Русский"

def test_web_loader_blocks_loopback_and_allows_public_ip():
    loopback = [(2, 1, 6, "", ("127.0.0.1", 80))]
    with patch("llm_assistant.web_search.socket.getaddrinfo", return_value=loopback):
        allowed, _reason = WebSearchMixin._validate_public_web_url(
            "http://example.test/page"
        )
    assert not allowed

    public = [(2, 1, 6, "", ("93.184.216.34", 443))]
    with patch("llm_assistant.web_search.socket.getaddrinfo", return_value=public):
        allowed, reason = WebSearchMixin._validate_public_web_url(
            "https://example.test/page"
        )
    assert allowed, reason

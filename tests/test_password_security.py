import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from llm_assistant.security_manager import SecurityMixin
from llm_assistant.sessions import SessionMixin


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class SecureDummy(SecurityMixin, SessionMixin):
    def __init__(self):
        self._security_config = {}
        self._security_key = None
        self._security_unlocked = True
        self._session_name = "secure"
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
        self.chat_history = []
        self.loaded_files = {}
        self.current_project = None
        self.web_results = []

    def _context_token_breakdown(self):
        return {"total": 0, "chat": 0, "files": 0, "web": 0}

    def _update_session_ui(self):
        pass


def test_password_verifier_and_authenticated_encryption():
    app = SecureDummy()
    config, key = app._security_new_config("correct horse battery staple")
    app._security_config = config
    app._security_key = key

    assert app._security_verify_password("correct horse battery staple") == key
    assert app._security_verify_password("wrong password") is None

    encrypted = app._security_encrypt_bytes(b"private session", "session")
    assert b"private session" not in encrypted
    assert app._security_decrypt_bytes(encrypted, "session") == b"private session"

    damaged = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
    with pytest.raises(ValueError):
        app._security_decrypt_bytes(damaged, "session")


def test_session_is_saved_encrypted_when_password_is_enabled():
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        app = SecureDummy()
        config, key = app._security_new_config("a strong local password")
        app._security_config = config
        app._security_key = key

        with patch("llm_assistant.sessions.SESSION_DIR", base):
            assert app._save_session("secure", silent=True)
            path = base / "secure.llms"
            assert path.exists()
            assert not (base / "secure.json").exists()
            raw = path.read_bytes()
            assert b'"server_name"' not in raw
            data = app._read_session_data(path)

        assert data["server_name"] == "Ollama"
        assert data["model"] == "qwen3:4b"
        assert data["version"] == 16


def test_plaintext_session_migration_round_trip():
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        original = {"name": "old", "chat_history": [{"role": "user", "content": "secret"}]}
        (base / "old.json").write_text(json.dumps(original), encoding="utf-8")

        app = SecureDummy()
        config, key = app._security_new_config("migration password")
        app._security_config = config
        app._security_key = key

        with patch("llm_assistant.security_manager.SESSION_DIR", base):
            app._security_encrypt_plaintext_sessions_with_key(key)
            assert not (base / "old.json").exists()
            assert (base / "old.llms").exists()
            assert b"secret" not in (base / "old.llms").read_bytes()

            app._security_decrypt_sessions_with_key(key)
            assert not (base / "old.llms").exists()
            restored = json.loads((base / "old.json").read_text(encoding="utf-8"))

        assert restored == original


def test_startup_unlock_is_optional_and_accepts_correct_password():
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        config_path = base / "security.json"
        sessions = base / "sessions"
        sessions.mkdir()

        app = SecureDummy()
        config, expected_key = app._security_new_config("startup password")
        config_path.write_text(json.dumps(config), encoding="utf-8")
        app._security_password_prompt = lambda **_kwargs: "startup password"

        with patch("llm_assistant.security_manager.SECURITY_CONFIG_PATH", config_path), patch(
            "llm_assistant.security_manager.SECURITY_DIR", base
        ), patch("llm_assistant.security_manager.SESSION_DIR", sessions):
            assert app._security_startup_unlock()

        assert app._security_key == expected_key
        assert app._security_unlocked

        # With no config at all, startup must not ask for a password.
        config_path.unlink()
        app2 = SecureDummy()
        app2._security_password_prompt = lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("password prompt should not be shown")
        )
        with patch("llm_assistant.security_manager.SECURITY_CONFIG_PATH", config_path), patch(
            "llm_assistant.security_manager.SECURITY_DIR", base
        ), patch("llm_assistant.security_manager.SESSION_DIR", sessions):
            assert app2._security_startup_unlock()

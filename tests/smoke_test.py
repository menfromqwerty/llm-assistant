"""Быстрая проверка структуры и умного контекста без сетевых запросов."""

from pathlib import Path
from tempfile import TemporaryDirectory

from llm_assistant.app import LLMAssistant
from llm_assistant.common import DEFAULT_MODEL_NAME

def test_class_assembly() -> None:
    assert DEFAULT_MODEL_NAME == "qwen/qwen3-coder-30b"
    assert LLMAssistant._tok("12345678") == 2
    assert LLMAssistant._short_model_name(DEFAULT_MODEL_NAME) == "qwen3-coder-30b"
    for method in (
        "_save_session",
        "_reset_context",
        "_start_lm_studio_server",
        "_check_connection",
        "_classify_api_error",
        "_build_file_context",
        "_preview_context_selection",
        "_select_all_context_files",
    ):
        assert hasattr(LLMAssistant, method), method

def test_smart_context() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "main.py").write_text(
            "from server_manager import ServerManager\nprint('start')\n",
            encoding="utf-8",
        )
        (root / "server_manager.py").write_text(
            "class ServerManager:\n"
            "    def reconnect(self):\n"
            "        return 'LM Studio server'\n",
            encoding="utf-8",
        )
        (root / "unrelated.py").write_text(
            "def draw_cat():\n    return 'cat'\n",
            encoding="utf-8",
        )

        app = LLMAssistant.__new__(LLMAssistant)
        app.loaded_files = {
            path.name: str(path)
            for path in root.glob("*.py")
        }
        app._file_context_selected = {
            name: False for name in app.loaded_files
        }

        options = {
            "mode": "auto",
            "budget": 2000,
            "selected_files": [],
            "loaded_files": dict(app.loaded_files),
        }
        _context, used, summary = app._build_file_context(
            "Проверь reconnect в server_manager.py",
            options,
        )
        included = [item["name"] for item in summary["included"]]
        assert "server_manager.py" in included
        assert used <= 2000

        selected_options = {
            "mode": "selected",
            "budget": 2000,
            "selected_files": ["unrelated.py"],
            "loaded_files": dict(app.loaded_files),
        }
        _context, _used, selected_summary = app._build_file_context(
            "Проверь файл",
            selected_options,
        )
        assert [item["name"] for item in selected_summary["included"]] == [
            "unrelated.py"
        ]

if __name__ == "__main__":
    test_class_assembly()
    test_smart_context()
    print("SMOKE_TEST_OK")

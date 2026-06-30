from llm_assistant.common import DEFAULT_LANGUAGE_MODE, LANGUAGE_PROFILES
from llm_assistant.language_manager import LanguageManagerMixin


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Dummy(LanguageManagerMixin):
    def __init__(self):
        self._language_var = Var(DEFAULT_LANGUAGE_MODE)


def test_default_language_is_bilingual_interface():
    app = Dummy()
    assert app._language_var.get() == "English + Русский"
    assert app._ui_language_code() == "bi"
    assert app._language_button_text() == "🌐 EN + RU"
    assert app._translate_literal("📄 Файл") == "📄 File / Файл"


def test_russian_and_english_translate_immediately():
    app = Dummy()
    app._language_var.set("English")
    assert app._translate_literal("📋 Шаблоны") == "📋 Templates"
    assert app._translate_literal("🧹 ОЧИСТИТЬ") == "🧹 CLEAR"
    app._language_var.set("Русский")
    assert app._translate_literal("📋 Templates") == "📋 Шаблоны"


def test_language_selector_does_not_force_model_language():
    app = Dummy()
    instruction = app._language_instruction().lower()
    assert "языке последнего запроса" in instruction
    for mode in LANGUAGE_PROFILES:
        app._language_var.set(mode)
        assert app._language_instruction().lower() == instruction


def test_all_profiles_have_button_and_ui_code():
    app = Dummy()
    for mode, profile in LANGUAGE_PROFILES.items():
        app._language_var.set(mode)
        assert app._language_button_text() == profile["button"]
        assert profile["ui"] in {"ru", "en", "bi", "auto"}

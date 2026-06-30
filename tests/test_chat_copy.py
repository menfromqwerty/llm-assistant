from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_SOURCE = (ROOT / "llm_assistant" / "ui.py").read_text(encoding="utf-8")
LLM_SOURCE = (ROOT / "llm_assistant" / "llm_client.py").read_text(encoding="utf-8")


def test_bright_chat_selection_is_configured():
    assert '"selection_bg": "#ffd740"' in UI_SOURCE
    assert 'selectforeground=self.C["selection_fg"]' in UI_SOURCE
    assert 'exportselection=False' in UI_SOURCE
    assert 'widget.tag_raise(tk.SEL)' in UI_SOURCE


def test_copy_shortcuts_and_feedback_exist():
    assert '"<Control-c>"' in UI_SOURCE
    assert '"<Control-a>"' in UI_SOURCE
    assert '"<Escape>"' in UI_SOURCE
    assert 'def _show_copy_toast' in UI_SOURCE
    assert 'Скопировано:' in UI_SOURCE


def test_new_code_tags_do_not_hide_selection():
    assert 'self._raise_selection_tag(self.chat_text)' in LLM_SOURCE

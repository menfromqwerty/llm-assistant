"""Tests for unified Send/Stop generation control."""

import threading

from llm_assistant.llm_client import LLMClientMixin


class Button:
    def __init__(self):
        self.options = {}

    def config(self, **kwargs):
        self.options.update(kwargs)

    @property
    def state(self):
        return self.options.get("state")

    @property
    def text(self):
        return self.options.get("text", "")


class Status:
    def __init__(self):
        self.text = ""

    def config(self, **kwargs):
        self.text = kwargs.get("text", self.text)


class Closable:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class Dummy(LLMClientMixin):
    def __init__(self):
        self.is_loading = True
        self._cancel_generation_event = threading.Event()
        self._action_btn = Button()
        # Compatibility aliases used by the real UI.
        self._send_btn = self._action_btn
        self._stop_btn = self._action_btn
        self.C = {"accent": "#00aaaa", "accent2": "#00cccc"}
        self._status = Status()
        self._active_response = Closable()
        self._active_http_session = Closable()
        self.sent = 0
        self.stopped = 0

    def _send_message(self):
        self.sent += 1

    def _stop_generation(self):
        self.stopped += 1
        return super()._stop_generation()


def test_stop_generation_closes_transport_and_sets_event():
    app = Dummy()
    response = app._active_response
    session = app._active_http_session

    app._stop_generation()

    assert app._cancel_generation_event.is_set()
    assert response.closed is True
    assert session.closed is True
    assert app._action_btn.state == "disabled"
    assert "Останавливаю" in app._action_btn.text
    assert "Остановка" in app._status.text


def test_generation_control_changes_same_button():
    app = Dummy()

    app._set_generation_controls(True)
    assert app._action_btn.state == "normal"
    assert app._action_btn.text == "■ Остановить"
    assert app._action_btn.options["bg"] == "#b74343"

    app._set_generation_controls(False)
    assert app._action_btn.state == "normal"
    assert app._action_btn.text == "➤ Отправить"
    assert app._action_btn.options["bg"] == "#00aaaa"


def test_repeated_action_stops_instead_of_sending_again():
    app = Dummy()
    app.is_loading = False
    app._send_or_stop()
    assert app.sent == 1
    assert app.stopped == 0

    app.is_loading = True
    app._send_or_stop()
    assert app.sent == 1
    assert app.stopped == 1


if __name__ == "__main__":
    test_stop_generation_closes_transport_and_sets_event()
    test_generation_control_changes_same_button()
    test_repeated_action_stops_instead_of_sending_again()
    print("TOGGLE_STOP_TEST_OK")

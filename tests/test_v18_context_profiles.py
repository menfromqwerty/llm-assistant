from llm_assistant.app import LLMAssistant


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class ProfileDummy:
    _runtime_profile_key = LLMAssistant._runtime_profile_key
    _save_active_runtime_profile = LLMAssistant._save_active_runtime_profile
    _restore_runtime_profile = LLMAssistant._restore_runtime_profile
    _profile_for_model = LLMAssistant._profile_for_model
    _effective_context_window = LLMAssistant._effective_context_window
    _effective_input_budget = LLMAssistant._effective_input_budget

    def __init__(self):
        self._runtime_profiles = {}
        self._server_var = Var("LM Studio")
        self._model_name = "model-a"
        self._context_window_var = Var(32768)
        self._max_tokens_var = Var(4096)
        self._temperature_var = Var(0.2)
        self._think_var = Var(False)


def test_context_budget_reserves_output_and_safety():
    app = ProfileDummy()
    assert app._effective_context_window() == 32768
    assert app._effective_input_budget() == 27689


def test_runtime_profiles_are_per_server_and_model():
    app = ProfileDummy()
    app._save_active_runtime_profile()

    app._model_name = "model-b"
    app._context_window_var.set(65536)
    app._max_tokens_var.set(8192)
    app._temperature_var.set(0.6)
    app._think_var.set(True)
    app._save_active_runtime_profile()

    app._model_name = "model-a"
    app._context_window_var.set(4096)
    restored = app._restore_runtime_profile(apply_recommended=False)

    assert restored is True
    assert app._context_window_var.get() == 32768
    assert app._max_tokens_var.get() == 4096
    assert app._temperature_var.get() == 0.2
    assert app._think_var.get() is False

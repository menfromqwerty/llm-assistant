from unittest.mock import patch

from llm_assistant.server_manager import ServerManagerMixin


class DummyResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = str(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            response = self
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = response
            raise error


class Dummy(ServerManagerMixin):
    pass


def test_ollama_native_fallback():
    dummy = Dummy()
    replies = [
        DummyResponse(404, {"error": "not found"}),
        DummyResponse(200, {"models": [{"name": "qwen3:8b"}, {"model": "gemma4"}]}),
    ]
    with patch("llm_assistant.server_manager.requests.get", side_effect=replies):
        models = dummy._fetch_server_models("Ollama", "http://localhost:11434/v1")
    assert models == ["gemma4", "qwen3:8b"]


def test_openai_models():
    dummy = Dummy()
    reply = DummyResponse(200, {"data": [{"id": "alpha"}, {"id": "beta"}]})
    with patch("llm_assistant.server_manager.requests.get", return_value=reply):
        models = dummy._fetch_server_models("LM Studio", "http://localhost:1234/v1")
    assert models == ["alpha", "beta"]


if __name__ == "__main__":
    test_ollama_native_fallback()
    test_openai_models()
    print("MULTI_SERVER_TEST_OK")

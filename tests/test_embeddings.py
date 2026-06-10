import json

import pytest

from local_code_indexer.embeddings import LocalEmbedder


def test_local_embedder_rejects_non_localhost_urls() -> None:
    with pytest.raises(ValueError, match="local"):
        LocalEmbedder(base_url="https://api.openai.com").embed("hello")


def test_local_embedder_posts_only_to_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return json.dumps({"embeddings": [[0.1, 0.2, 0.3]]}).encode()

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["body"] = json.loads(request.data.decode())
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    vector = LocalEmbedder(base_url="http://127.0.0.1:11434").embed("local code")

    assert vector == [0.1, 0.2, 0.3]
    assert str(seen["url"]).startswith("http://127.0.0.1:11434/api/embed")
    assert seen["body"] == {"model": "nomic-embed-text", "input": "local code"}


def test_local_embedder_supports_legacy_ollama_embedding_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return json.dumps({"embedding": [0.4, 0.5]}).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    assert LocalEmbedder().embed("fallback") == [0.4, 0.5]

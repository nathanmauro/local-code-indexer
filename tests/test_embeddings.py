import json
import urllib.error

import pytest

from local_code_indexer.embeddings import LocalEmbedder


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def capture_urlopen(monkeypatch: pytest.MonkeyPatch, payload: dict) -> list[dict]:
    requests: list[dict] = []

    def fake_urlopen(request, timeout):
        requests.append(
            {
                "url": request.full_url,
                "body": json.loads(request.data.decode()),
                "timeout": timeout,
            }
        )
        return FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return requests


def forbid_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_urlopen(request, timeout):
        raise AssertionError("no HTTP request should have been made")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)


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
    assert seen["body"] == {
        "model": "nomic-embed-text",
        "input": "local code",
        "keep_alive": "10m",
    }


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


def test_embed_batch_posts_one_request_per_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = capture_urlopen(
        monkeypatch, {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
    )

    vectors = LocalEmbedder().embed_batch(["first chunk", "second chunk"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert len(requests) == 1
    assert requests[0]["url"] == "http://127.0.0.1:11434/api/embed"
    assert requests[0]["body"] == {
        "model": "nomic-embed-text",
        "input": ["first chunk", "second chunk"],
        "keep_alive": "10m",
    }


def test_embed_batch_returns_none_per_text_on_batch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", failing_urlopen)

    assert LocalEmbedder().embed_batch(["a", "b", "c"]) == [None, None, None]


def test_embed_batch_returns_none_per_text_on_wrong_length_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_urlopen(monkeypatch, {"embeddings": [[0.1, 0.2]]})

    assert LocalEmbedder().embed_batch(["a", "b"]) == [None, None]


def test_embed_batch_empty_input_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    forbid_urlopen(monkeypatch)

    assert LocalEmbedder().embed_batch([]) == []


def test_embed_batch_rejects_non_localhost_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    forbid_urlopen(monkeypatch)

    for api in ("ollama", "openai"):
        with pytest.raises(ValueError, match="local"):
            LocalEmbedder(base_url="https://api.openai.com", api=api).embed_batch(["hello"])


def test_openai_api_embed_rejects_non_localhost_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    forbid_urlopen(monkeypatch)

    with pytest.raises(ValueError, match="local"):
        LocalEmbedder(base_url="https://api.openai.com", api="openai").embed("hello")


def test_openai_api_embed_uses_v1_embeddings_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = capture_urlopen(monkeypatch, {"data": [{"embedding": [0.7, 0.8]}]})

    vector = LocalEmbedder(base_url="http://127.0.0.1:1234", api="openai").embed("local code")

    assert vector == [0.7, 0.8]
    assert len(requests) == 1
    assert requests[0]["url"] == "http://127.0.0.1:1234/v1/embeddings"
    assert requests[0]["body"] == {"model": "nomic-embed-text", "input": ["local code"]}


def test_openai_api_embed_batch_uses_v1_embeddings_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = capture_urlopen(
        monkeypatch, {"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
    )

    vectors = LocalEmbedder(base_url="http://localhost:1234", api="openai").embed_batch(
        ["one", "two"]
    )

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert len(requests) == 1
    assert requests[0]["url"] == "http://localhost:1234/v1/embeddings"
    assert requests[0]["body"] == {"model": "nomic-embed-text", "input": ["one", "two"]}


def test_openai_api_embed_batch_honors_response_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    capture_urlopen(
        monkeypatch,
        {
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        },
    )

    vectors = LocalEmbedder(base_url="http://localhost:1234", api="openai").embed_batch(
        ["one", "two"]
    )

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embedder_rejects_unknown_api() -> None:
    with pytest.raises(ValueError, match="api"):
        LocalEmbedder(api="bogus")


def test_embedder_defaults_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_EMBED_URL", "http://localhost:1234/")
    monkeypatch.setenv("LOCAL_CODE_INDEXER_EMBED_MODEL", "custom-embed")
    monkeypatch.setenv("LOCAL_CODE_INDEXER_EMBED_API", "openai")

    embedder = LocalEmbedder()

    assert embedder.base_url == "http://localhost:1234"
    assert embedder.model == "custom-embed"
    assert embedder.api == "openai"


def test_embedder_constructor_args_override_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_EMBED_URL", "http://localhost:1234")
    monkeypatch.setenv("LOCAL_CODE_INDEXER_EMBED_MODEL", "custom-embed")
    monkeypatch.setenv("LOCAL_CODE_INDEXER_EMBED_API", "openai")

    embedder = LocalEmbedder(
        base_url="http://127.0.0.1:11434", model="nomic-embed-text", api="ollama"
    )

    assert embedder.base_url == "http://127.0.0.1:11434"
    assert embedder.model == "nomic-embed-text"
    assert embedder.api == "ollama"

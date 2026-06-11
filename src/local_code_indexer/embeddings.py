"""Local-only embedding client."""

from __future__ import annotations

import json
import urllib.request
from urllib.parse import urlparse

from . import config

# Asks Ollama to keep the model resident between requests so bulk reindex
# passes don't pay a cold model load each time.
OLLAMA_KEEP_ALIVE = "10m"


class LocalEmbedder:
    """Ollama- or OpenAI-compatible embedder restricted to loopback hosts."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        api: str | None = None,
    ):
        self.base_url = (base_url or config.embed_url_from_env()).rstrip("/")
        self.model = model or config.embed_model_from_env()
        self.timeout = timeout
        self.api = api or config.embed_api_from_env()
        if self.api not in {"ollama", "openai"}:
            raise ValueError(f"Unsupported embedding api: {self.api!r} (use 'ollama' or 'openai')")

    def _validate_localhost(self) -> None:
        parsed = urlparse(self.base_url)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Embedding base_url must point to a local loopback service.")

    def _post_json(self, path: str, body: dict) -> dict:
        self._validate_localhost()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode())

    def embed(self, text: str) -> list[float]:
        if self.api == "openai":
            payload = self._post_json("/v1/embeddings", {"model": self.model, "input": [text]})
            data = payload.get("data") or []
            if data:
                return [float(value) for value in data[0]["embedding"]]
            raise RuntimeError("Local embedding service returned no embedding vector.")

        payload = self._post_json(
            "/api/embed",
            {"model": self.model, "input": text, "keep_alive": OLLAMA_KEEP_ALIVE},
        )
        if "embeddings" in payload and payload["embeddings"]:
            return [float(value) for value in payload["embeddings"][0]]
        if "embedding" in payload:
            return [float(value) for value in payload["embedding"]]
        raise RuntimeError("Local embedding service returned no embedding vector.")

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Embed a batch with one HTTP request; a batch-level failure yields all Nones."""
        if not texts:
            return []
        self._validate_localhost()
        try:
            if self.api == "openai":
                payload = self._post_json("/v1/embeddings", {"model": self.model, "input": texts})
                vectors = [item["embedding"] for item in payload["data"]]
            else:
                payload = self._post_json(
                    "/api/embed",
                    {"model": self.model, "input": texts, "keep_alive": OLLAMA_KEEP_ALIVE},
                )
                vectors = payload["embeddings"]
            if len(vectors) != len(texts):
                return [None] * len(texts)
            return [[float(value) for value in vector] for vector in vectors]
        except Exception:
            return [None] * len(texts)

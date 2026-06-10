"""Local-only embedding client."""

from __future__ import annotations

import json
import urllib.request
from urllib.parse import urlparse


class LocalEmbedder:
    """Ollama-compatible embedder restricted to loopback hosts."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "nomic-embed-text",
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _validate_localhost(self) -> None:
        parsed = urlparse(self.base_url)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Embedding base_url must point to a local loopback service.")

    def embed(self, text: str) -> list[float]:
        self._validate_localhost()
        body = json.dumps({"model": self.model, "input": text}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode())

        if "embeddings" in payload and payload["embeddings"]:
            return [float(value) for value in payload["embeddings"][0]]
        if "embedding" in payload:
            return [float(value) for value in payload["embedding"]]
        raise RuntimeError("Local embedding service returned no embedding vector.")

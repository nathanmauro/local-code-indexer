"""Runtime configuration for the local code indexer."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_HOME = Path("~/.local/share/local-code-indexer").expanduser()
DEFAULT_DB_PATH = DEFAULT_HOME / "index.db"


def db_path_from_env() -> Path:
    return Path(os.environ.get("LOCAL_CODE_INDEXER_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()


def embeddings_disabled() -> bool:
    return os.environ.get("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def embed_url_from_env() -> str:
    return os.environ.get("LOCAL_CODE_INDEXER_EMBED_URL", "http://127.0.0.1:11434")


def embed_model_from_env() -> str:
    return os.environ.get("LOCAL_CODE_INDEXER_EMBED_MODEL", "nomic-embed-text")


def embed_api_from_env() -> str:
    return os.environ.get("LOCAL_CODE_INDEXER_EMBED_API", "ollama")


DEFAULT_LOW_CONFIDENCE_SIMILARITY = 0.6


def low_confidence_similarity_from_env() -> float:
    raw = os.environ.get("LOCAL_CODE_INDEXER_LOW_CONFIDENCE_SIMILARITY", "").strip()
    if not raw:
        return DEFAULT_LOW_CONFIDENCE_SIMILARITY
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_LOW_CONFIDENCE_SIMILARITY

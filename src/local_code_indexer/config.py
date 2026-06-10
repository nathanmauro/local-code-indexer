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

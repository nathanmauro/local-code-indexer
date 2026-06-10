"""Repository file scanning."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from .ignore import HARD_SKIP_DIRS, IgnoreMatcher


def iter_indexable_files(root: Path, matcher: IgnoreMatcher | None = None) -> Iterator[Path]:
    root = Path(root).resolve()
    matcher = matcher or IgnoreMatcher(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in HARD_SKIP_DIRS and not (current / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = current / filename
            if matcher.is_indexable(path):
                yield path

"""Ignore rules for local repository indexing."""

from __future__ import annotations

import os
from pathlib import Path

import pathspec

IGNORE_FILES = (".gitignore", ".augmentignore", ".indexignore")
HARD_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    ".cache",
    ".gradle",
    ".turbo",
    "node_modules",
    "vendor",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "target",
    "coverage",
}
SECRET_NAMES = {
    ".netrc",
    ".pgpass",
    ".htpasswd",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}
# Any .env, .envrc, .env.production, .env.staging.local, ... variant.
SECRET_ENV_NAMES = {".env", ".envrc"}
SECRET_ENV_PREFIX = ".env."
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".der", ".jks", ".keystore", ".ppk")
LOCKFILE_NAMES = {
    "uv.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
    "Gemfile.lock",
    "composer.lock",
    "go.sum",
}


def _translate_pattern(prefix: str, line: str) -> str | None:
    """Rewrite a pattern from a nested ignore file so it is root-relative.

    Follows gitignore semantics: a leading slash (or any interior slash) anchors the
    pattern to the ignore file's directory; otherwise it matches at any depth below it.
    """
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    if not prefix:
        return line
    negated = line.startswith("!")
    body = line[1:] if negated else line
    if body.startswith("/"):
        translated = f"{prefix}{body}"
    elif "/" in body.rstrip("/"):
        translated = f"{prefix}/{body}"
    else:
        translated = f"{prefix}/**/{body}"
    return f"!{translated}" if negated else translated


class IgnoreMatcher:
    def __init__(self, root: Path, max_file_bytes: int = 1_000_000):
        self.root = Path(root).resolve()
        self.max_file_bytes = max_file_bytes
        self._spec = self._load_spec()

    def _load_spec(self) -> pathspec.PathSpec:
        lines: list[str] = []
        for ignore_dir in self._iter_ignore_dirs():
            prefix = ignore_dir.relative_to(self.root).as_posix()
            prefix = "" if prefix == "." else prefix
            for filename in IGNORE_FILES:
                ignore_path = ignore_dir / filename
                if ignore_path.is_file():
                    for raw in ignore_path.read_text(errors="ignore").splitlines():
                        translated = _translate_pattern(prefix, raw)
                        if translated is not None:
                            lines.append(translated)
        return pathspec.PathSpec.from_lines("gitignore", lines)

    def _iter_ignore_dirs(self) -> list[Path]:
        directories: list[Path] = []
        for dirpath, dirnames, _filenames in os.walk(self.root, followlinks=False):
            current = Path(dirpath)
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in HARD_SKIP_DIRS and not (current / name).is_symlink()
            )
            directories.append(current)
        return directories

    def _relative(self, path: Path) -> str:
        try:
            rel = path.resolve().relative_to(self.root)
        except ValueError:
            rel = path
        return rel.as_posix()

    def _hard_skip(self, path: Path) -> bool:
        rel_parts = Path(self._relative(path)).parts
        if any(part in HARD_SKIP_DIRS for part in rel_parts):
            return True
        name = path.name
        if name in SECRET_NAMES or name in LOCKFILE_NAMES:
            return True
        if name in SECRET_ENV_NAMES or name.startswith(SECRET_ENV_PREFIX):
            return True
        return name.endswith(SECRET_SUFFIXES)

    def _looks_binary(self, path: Path) -> bool:
        try:
            with path.open("rb") as handle:
                sample = handle.read(4096)
        except OSError:
            return True
        if b"\x00" in sample:
            return True
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError as error:
            # A multibyte sequence cut off by the 4096-byte window is truncation,
            # not binary content; UTF-8 sequences are at most 4 bytes long.
            if error.start < len(sample) - 3:
                return True
        return False

    def is_indexable(self, path: Path) -> bool:
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            return False
        if self._hard_skip(path):
            return False
        rel = self._relative(path)
        if self._spec.match_file(rel):
            return False
        try:
            if path.stat().st_size > self.max_file_bytes:
                return False
        except OSError:
            return False
        return not self._looks_binary(path)

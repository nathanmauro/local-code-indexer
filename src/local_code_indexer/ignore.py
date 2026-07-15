"""Ignore rules for local repository indexing."""

from __future__ import annotations

import os
import subprocess
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


def _resolve_git_dir(directory: Path) -> Path | None:
    """Return the git directory for a repository rooted at *directory*, if any.

    Linked worktrees and submodules keep a ``gitdir: <path>`` pointer file instead of
    a ``.git`` directory; shared files such as ``info/exclude`` live in the common git
    directory that ``commondir`` points to.
    """
    dot_git = directory / ".git"
    if dot_git.is_dir():
        return dot_git
    if not dot_git.is_file():
        return None
    pointer = dot_git.read_text(errors="ignore").strip()
    if not pointer.startswith("gitdir:"):
        return None
    git_dir = Path(pointer.removeprefix("gitdir:").strip())
    if not git_dir.is_absolute():
        git_dir = (directory / git_dir).resolve()
    commondir = git_dir / "commondir"
    if commondir.is_file():
        common = Path(commondir.read_text(errors="ignore").strip())
        git_dir = common if common.is_absolute() else (git_dir / common).resolve()
    return git_dir if git_dir.is_dir() else None


def _core_excludes_file(directory: Path) -> Path | None:
    """Resolve ``core.excludesFile`` the way git does.

    Asks ``git config`` so all config levels apply, then falls back to git's built-in
    default location when the key is unset or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "config", "--path", "--get", "core.excludesFile"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        configured = result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        configured = ""
    if configured:
        return Path(configured)
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config_home:
        return Path(xdg_config_home) / "git" / "ignore"
    try:
        return Path.home() / ".config" / "git" / "ignore"
    except RuntimeError:
        return None


def _git_exclude_files(directory: Path) -> list[Path]:
    """Repository-level exclude files for *directory*, lowest precedence first."""
    git_dir = _resolve_git_dir(directory)
    if git_dir is None:
        return []
    candidates = [_core_excludes_file(directory), git_dir / "info" / "exclude"]
    return [path for path in candidates if path is not None and path.is_file()]


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
            # Git excludes come first so a .gitignore in the same directory keeps
            # higher precedence (the last matching pattern wins).
            sources = _git_exclude_files(ignore_dir)
            sources += [ignore_dir / filename for filename in IGNORE_FILES]
            for ignore_path in sources:
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

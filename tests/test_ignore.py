import shutil
from pathlib import Path

import pytest

from local_code_indexer.ignore import IgnoreMatcher
from local_code_indexer.scanner import iter_indexable_files


def write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data)


def isolate_git_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Keep the developer's real git config and global excludes out of the test."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return home


def test_ignore_matcher_honors_repo_ignores_and_hard_skips(tmp_path: Path) -> None:
    write(tmp_path / ".gitignore", "ignored.log\nnode_modules/\n")
    write(tmp_path / ".augmentignore", "augment-only.txt\n")
    write(tmp_path / ".indexignore", "private/**\n")
    write(tmp_path / "src/app.py", "def run():\n    return 'ok'\n")
    write(tmp_path / "ignored.log", "ignored by gitignore")
    write(tmp_path / "augment-only.txt", "ignored by augmentignore")
    write(tmp_path / "private/secret.py", "TOKEN = 'x'")
    write(tmp_path / "node_modules/pkg/index.js", "export const x = 1")
    write(tmp_path / ".env", "OPENAI_API_KEY=secret")
    write(tmp_path / ".cache/tool/result.json", '{"cached": true}')
    write(tmp_path / "uv.lock", "[[package]]")
    write(tmp_path / "sub/package-lock.json", '{"lockfileVersion": 3}')
    write(tmp_path / "image.bin", b"\x00\x01\x02\x03")
    write(tmp_path / "huge.txt", "x" * 64)

    matcher = IgnoreMatcher(tmp_path, max_file_bytes=32)

    assert matcher.is_indexable(tmp_path / "src/app.py")
    assert not matcher.is_indexable(tmp_path / "ignored.log")
    assert not matcher.is_indexable(tmp_path / "augment-only.txt")
    assert not matcher.is_indexable(tmp_path / "private/secret.py")
    assert not matcher.is_indexable(tmp_path / "node_modules/pkg/index.js")
    assert not matcher.is_indexable(tmp_path / ".env")
    assert not matcher.is_indexable(tmp_path / ".cache/tool/result.json")
    assert not matcher.is_indexable(tmp_path / "uv.lock")
    assert not matcher.is_indexable(tmp_path / "sub/package-lock.json")
    assert not matcher.is_indexable(tmp_path / "image.bin")
    assert not matcher.is_indexable(tmp_path / "huge.txt")


def test_secret_name_variants_are_hard_skipped(tmp_path: Path) -> None:
    matcher = IgnoreMatcher(tmp_path)
    for name in (
        ".env.production",
        ".env.staging.local",
        ".netrc",
        ".pgpass",
        ".htpasswd",
        "server.der",
        "keystore.jks",
        "release.keystore",
        "putty.ppk",
    ):
        write(tmp_path / name, "secret material")
        assert not matcher.is_indexable(tmp_path / name), name


def test_utf8_multibyte_at_sniff_boundary_is_not_binary(tmp_path: Path) -> None:
    content = b"# " + b"x" * 4093 + "é".encode() + b"\ndef ok():\n    pass\n"
    write(tmp_path / "big.py", content)

    matcher = IgnoreMatcher(tmp_path)

    assert matcher.is_indexable(tmp_path / "big.py")
    write(tmp_path / "real.bin", b"\xff\xfe" + b"\x00" * 64)
    assert not matcher.is_indexable(tmp_path / "real.bin")


def test_symlinks_are_never_indexed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    write(outside / "private.txt", "secret key material")
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")
    (repo / "link.py").symlink_to(outside / "private.txt")
    (repo / "linkdir").symlink_to(outside, target_is_directory=True)

    matcher = IgnoreMatcher(repo)

    assert not matcher.is_indexable(repo / "link.py")
    assert list(iter_indexable_files(repo, matcher)) == [repo / "app.py"]


def test_nested_ignore_files_are_honored(tmp_path: Path) -> None:
    write(tmp_path / "src/app.py", "def run():\n    return 'ok'\n")
    write(tmp_path / "src/.gitignore", "generated.py\n/local-only.py\n")
    write(tmp_path / "src/generated.py", "x = 1\n")
    write(tmp_path / "src/deep/generated.py", "x = 1\n")
    write(tmp_path / "src/local-only.py", "x = 1\n")
    write(tmp_path / "src/deep/local-only.py", "x = 1\n")

    matcher = IgnoreMatcher(tmp_path)

    assert matcher.is_indexable(tmp_path / "src/app.py")
    assert not matcher.is_indexable(tmp_path / "src/generated.py")
    assert not matcher.is_indexable(tmp_path / "src/deep/generated.py")
    assert not matcher.is_indexable(tmp_path / "src/local-only.py")
    assert matcher.is_indexable(tmp_path / "src/deep/local-only.py")


def test_git_info_exclude_is_honored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    isolate_git_env(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    write(repo / ".git/info/exclude", "/.worktrees/\nscratch.txt\n")
    write(repo / "src/app.py", "def run():\n    return 'ok'\n")
    write(repo / ".worktrees/wt1/src/app.py", "def run():\n    return 'duplicate'\n")
    write(repo / "scratch.txt", "local scratch")
    write(repo / "sub/scratch.txt", "local scratch")

    matcher = IgnoreMatcher(repo)

    assert matcher.is_indexable(repo / "src/app.py")
    assert not matcher.is_indexable(repo / ".worktrees/wt1/src/app.py")
    assert not matcher.is_indexable(repo / "scratch.txt")
    assert not matcher.is_indexable(repo / "sub/scratch.txt")
    assert list(iter_indexable_files(repo, matcher)) == [repo / "src/app.py"]


def test_git_info_exclude_yields_to_gitignore_negation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolate_git_env(monkeypatch, tmp_path)
    write(tmp_path / ".git/info/exclude", "*.log\n")
    write(tmp_path / ".gitignore", "!keep.log\n")
    write(tmp_path / "keep.log", "kept by gitignore negation")
    write(tmp_path / "other.log", "ignored by info/exclude")

    matcher = IgnoreMatcher(tmp_path)

    assert matcher.is_indexable(tmp_path / "keep.log")
    assert not matcher.is_indexable(tmp_path / "other.log")


def test_nested_repo_info_exclude_is_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolate_git_env(monkeypatch, tmp_path)
    write(tmp_path / "vendor/repo/.git/info/exclude", "generated.py\n")
    write(tmp_path / "vendor/repo/generated.py", "x = 1\n")
    write(tmp_path / "vendor/repo/deep/generated.py", "x = 1\n")
    write(tmp_path / "generated.py", "x = 1\n")

    matcher = IgnoreMatcher(tmp_path)

    assert not matcher.is_indexable(tmp_path / "vendor/repo/generated.py")
    assert not matcher.is_indexable(tmp_path / "vendor/repo/deep/generated.py")
    assert matcher.is_indexable(tmp_path / "generated.py")


def test_worktree_gitdir_pointer_resolves_shared_exclude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolate_git_env(monkeypatch, tmp_path)
    main = tmp_path / "main"
    write(main / ".git/info/exclude", "*.tmp\n")
    write(main / ".git/worktrees/wt/commondir", "../..\n")
    worktree = tmp_path / "wt"
    write(worktree / ".git", f"gitdir: {main / '.git/worktrees/wt'}\n")
    write(worktree / "app.py", "def run():\n    return 'ok'\n")
    write(worktree / "junk.tmp", "excluded by the shared info/exclude")

    matcher = IgnoreMatcher(worktree)

    assert matcher.is_indexable(worktree / "app.py")
    assert not matcher.is_indexable(worktree / "junk.tmp")


def test_default_global_excludes_apply_only_inside_repos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = isolate_git_env(monkeypatch, tmp_path)
    write(home / ".config/git/ignore", "*.scratch\n")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    write(repo / "app.py", "def run():\n    return 'ok'\n")
    write(repo / "notes.scratch", "excluded by the default global ignore file")
    plain = tmp_path / "plain"
    write(plain / "notes.scratch", "not a repo, so global excludes do not apply")

    matcher = IgnoreMatcher(repo)

    assert matcher.is_indexable(repo / "app.py")
    assert not matcher.is_indexable(repo / "notes.scratch")
    assert IgnoreMatcher(plain).is_indexable(plain / "notes.scratch")


@pytest.mark.skipif(shutil.which("git") is None, reason="requires git to resolve config")
def test_configured_core_excludes_file_is_honored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = isolate_git_env(monkeypatch, tmp_path)
    excludes = home / "global-excludes"
    write(excludes, "*.bak\n")
    write(home / ".gitconfig", f"[core]\n\texcludesFile = {excludes}\n")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    write(repo / "app.py", "def run():\n    return 'ok'\n")
    write(repo / "old.bak", "excluded by core.excludesFile")

    matcher = IgnoreMatcher(repo)

    assert matcher.is_indexable(repo / "app.py")
    assert not matcher.is_indexable(repo / "old.bak")

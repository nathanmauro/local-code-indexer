from pathlib import Path

from local_code_indexer.ignore import IgnoreMatcher
from local_code_indexer.scanner import iter_indexable_files


def write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data)


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

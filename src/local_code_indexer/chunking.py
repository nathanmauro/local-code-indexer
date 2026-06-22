"""Code chunking and symbol extraction."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

LANG_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cs": "c_sharp",
    ".kt": "kotlin",
    ".swift": "swift",
}

SYMBOL_PATTERNS = (
    (re.compile(r"^\s*class\s+([A-Za-z_][\w]*)", re.MULTILINE), "class"),
    (re.compile(r"^\s*def\s+([A-Za-z_][\w]*)", re.MULTILINE), "function"),
    (
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
        "function",
    ),
    (re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE), "class"),
    (
        re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
            re.MULTILINE,
        ),
        "function",
    ),
    (re.compile(r"^\s*func\s+([A-Za-z_][\w]*)", re.MULTILINE), "function"),
    (re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_][\w]*)", re.MULTILINE), "function"),
)


def split_lines(text: str) -> list[str]:
    """Split on newline only — not \\f/\\v/unicode breaks — so line numbers match
    editors, tree-sitter rows, and regex newline counting."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip("\r") for line in lines]


@dataclass(frozen=True)
class CodeChunk:
    id: str
    repo: str
    path: str
    start_line: int
    end_line: int
    content: str
    symbols: tuple[str, ...] = ()


def _language_for_path(path: str) -> str | None:
    for suffix, language in LANG_BY_SUFFIX.items():
        if path.endswith(suffix):
            return language
    return None


# tree-sitter-language-pack changed bindings across versions: older releases expose
# py-tree-sitter nodes (properties: .type/.start_point/.children, bytes input) while
# newer releases expose a Rust binding (methods: .kind()/.start_position()/.child(i),
# str input). These helpers normalize both shapes.
def _unwrap(value):
    return value() if callable(value) else value


def _node_kind(node) -> str:
    kind = getattr(node, "kind", None)
    if kind is not None:
        return _unwrap(kind)
    return getattr(node, "type", "")


def _node_children(node):
    children = getattr(node, "children", None)
    if children is not None and not callable(children):
        return children
    return [node.child(i) for i in range(_unwrap(node.child_count))]


def _node_start_row(node) -> int:
    position = getattr(node, "start_position", None)
    if position is not None:
        return _unwrap(position).row
    return node.start_point[0]


def _node_end_row(node) -> int:
    position = getattr(node, "end_position", None)
    if position is not None:
        return _unwrap(position).row
    return node.end_point[0]


def _symbol_kind(node_kind: str, parent_definition_kind: str | None = None) -> str:
    if node_kind in {"class_definition", "class_declaration"}:
        return "class"
    if node_kind in {"method_definition", "method_declaration"}:
        return "method"
    if node_kind in {"function_definition", "function_declaration"}:
        return "method" if parent_definition_kind == "class" else "function"
    return ""


def _tree_sitter_definitions(path: str, text: str) -> list[tuple[str, int, int, str]]:
    """Return (name, 1-based start line, 1-based end line, kind) for definitions."""
    language = _language_for_path(path)
    if not language:
        return []
    try:
        from tree_sitter_language_pack import get_parser
    except Exception:
        return []

    try:
        parser = get_parser(language)
        try:
            tree = parser.parse(text)
        except TypeError:
            tree = parser.parse(text.encode())
    except Exception:
        return []

    definitions: list[tuple[str, int, int, str]] = []
    source_bytes = text.encode()
    interesting = {
        "class_definition",
        "class_declaration",
        "function_definition",
        "function_declaration",
        "method_definition",
        "method_declaration",
    }

    def visit(node, parent_definition_kind: str | None = None) -> None:
        node_kind = _node_kind(node)
        if node_kind in interesting:
            name = node.child_by_field_name("name")
            if name is not None:
                start, end = _unwrap(name.start_byte), _unwrap(name.end_byte)
                value = source_bytes[start:end].decode(errors="ignore")
                if value:
                    definitions.append(
                        (
                            value,
                            _node_start_row(node) + 1,
                            _node_end_row(node) + 1,
                            _symbol_kind(node_kind, parent_definition_kind),
                        )
                    )
            parent_definition_kind = _symbol_kind(node_kind, parent_definition_kind)
        for child in _node_children(node):
            visit(child, parent_definition_kind)

    visit(_unwrap(tree.root_node))
    return definitions


def _tree_sitter_symbols(path: str, text: str) -> list[str]:
    return [name for name, _, _, _ in _tree_sitter_definitions(path, text)]


def _regex_symbol_definitions(text: str) -> list[tuple[str, int, str]]:
    results: list[tuple[str, int, str]] = []
    for pattern, kind in SYMBOL_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            results.append((match.group(1), line, kind))
    return results


def _regex_symbols(text: str) -> list[str]:
    return [name for name, _, _ in _regex_symbol_definitions(text)]


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)


def _chunk_id(repo: str, path: str, start_line: int, end_line: int, content: str) -> str:
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    raw = f"{repo}\0{path}\0{start_line}\0{end_line}\0{content_hash}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


def chunk_file_text(repo: str, path: str, text: str, max_lines: int = 80, overlap: int = 10) -> list[CodeChunk]:
    lines = split_lines(text)
    if not lines:
        return []
    max_lines = max(1, max_lines)
    overlap = max(0, min(overlap, max_lines - 1))
    symbols = extract_symbols(path, text)
    spans = sorted({(first, last) for _, first, last, _ in _tree_sitter_definitions(path, text)})
    chunks: list[CodeChunk] = []

    start = 0
    while start < len(lines):
        end = min(len(lines), start + max_lines)
        snapped = False
        if end < len(lines):
            # If the line window would cut a definition in half, break before it so the
            # next chunk starts at that tree-sitter definition boundary. Definitions that
            # fit entirely inside the window are left alone.
            snap = next(
                (first for first, last in spans if start + 1 < first <= end < last),
                None,
            )
            if snap is not None:
                end = snap - 1
                snapped = True
        content = "\n".join(lines[start:end])
        start_line = start + 1
        end_line = end
        chunk_symbols = tuple(
            symbol for symbol in symbols if re.search(rf"\b{re.escape(symbol)}\b", content)
        )
        chunks.append(
            CodeChunk(
                id=_chunk_id(repo, path, start_line, end_line, content),
                repo=repo,
                path=path,
                start_line=start_line,
                end_line=end_line,
                content=content,
                symbols=chunk_symbols,
            )
        )
        if end == len(lines):
            break
        start = end if snapped else end - overlap
    return chunks


def extract_symbol_definitions(path: str, text: str) -> list[tuple[str, int, str]]:
    """(name, 1-based definition line, kind) triples; tree-sitter first, regex fallback after."""
    definitions = [
        (name, start, kind) for name, start, _, kind in _tree_sitter_definitions(path, text)
    ]
    seen = {name for name, _, _ in definitions}
    for name, line, kind in _regex_symbol_definitions(text):
        if name not in seen:
            definitions.append((name, line, kind))
            seen.add(name)
    return definitions


def extract_symbols(path: str, text: str) -> tuple[str, ...]:
    return _dedupe([name for name, _, _ in extract_symbol_definitions(path, text)])

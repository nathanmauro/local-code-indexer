from local_code_indexer.chunking import chunk_file_text, extract_symbol_definitions, extract_symbols


def test_chunk_ids_are_stable_and_line_bounded() -> None:
    text = "\n".join(
        [
            "class AuthService:",
            "    def login(self, user):",
            "        return user.token",
            "",
            "def audit_event(name):",
            "    return name.lower()",
        ]
    )

    first = chunk_file_text("demo", "src/auth.py", text, max_lines=3, overlap=1)
    second = chunk_file_text("demo", "src/auth.py", text, max_lines=3, overlap=1)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert first[0].start_line == 1
    assert first[0].end_line == 3
    assert "AuthService" in first[0].symbols
    assert "login" in first[0].symbols
    assert all(chunk.end_line >= chunk.start_line for chunk in first)


def test_chunks_snap_to_tree_sitter_definition_boundaries() -> None:
    lines = ["def func_a(value):"]
    lines += [f"    a{i} = value + {i}" for i in range(10)]
    lines += ["    return a9", ""]
    lines += ["def func_b(value):"]  # line 14
    lines += [f"    b{i} = value * {i}" for i in range(10)]
    lines += ["    return b9"]
    text = "\n".join(lines)  # 25 lines total

    chunks = chunk_file_text("demo", "src/big.py", text, max_lines=20, overlap=5)

    assert chunks[0].end_line == 13
    assert chunks[1].start_line == 14
    assert "def func_b" not in chunks[0].content
    assert chunks[1].content.startswith("def func_b")


def test_symbol_definitions_report_definition_lines_not_first_mention() -> None:
    text = '"""Module that uses helper_fn for things."""\n\n\ndef helper_fn():\n    return 1\n'

    definitions = {
        name: (line, kind)
        for name, line, kind in extract_symbol_definitions("src/util.py", text)
    }

    assert definitions["helper_fn"] == (4, "function")


def test_symbol_extraction_supports_common_code_shapes() -> None:
    python_symbols = extract_symbols(
        "src/auth.py",
        "class AuthService:\n    def login(self):\n        pass\n",
    )
    typescript_symbols = extract_symbols(
        "src/tasks.ts",
        "export class TaskRunner {}\nexport function runTask() {}\nconst queueJob = () => true\n",
    )

    assert "AuthService" in python_symbols
    assert "login" in python_symbols
    assert "TaskRunner" in typescript_symbols
    assert "runTask" in typescript_symbols
    assert "queueJob" in typescript_symbols

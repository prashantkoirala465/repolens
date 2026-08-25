from repolens.chunking.code import chunk_code_file, naive_chunk_text

PY_SOURCE = '''\
import os

CONST = 1


def add(a, b):
    """Add two numbers."""
    return a + b


class Greeter:
    def greet(self, name):
        return f"hello {name}"
'''


def test_python_chunking_isolates_function_and_class() -> None:
    chunks = chunk_code_file("example.py", PY_SOURCE)
    symbols = {c.symbol for c in chunks if c.symbol}
    assert "add" in symbols
    assert "Greeter" in symbols


def test_python_function_chunk_is_self_contained() -> None:
    chunks = chunk_code_file("example.py", PY_SOURCE)
    add_chunk = next(c for c in chunks if c.symbol == "add")
    assert "def add(a, b):" in add_chunk.text
    assert "return a + b" in add_chunk.text
    # must not bleed into the next definition
    assert "class Greeter" not in add_chunk.text


def test_python_preamble_not_dropped() -> None:
    chunks = chunk_code_file("example.py", PY_SOURCE)
    all_text = "\n".join(c.text for c in chunks)
    assert "import os" in all_text
    assert "CONST = 1" in all_text


def test_unsupported_extension_falls_back_to_naive() -> None:
    chunks = chunk_code_file("example.rb", "def foo\n  1\nend\n")
    assert chunks
    assert chunks[0].symbol is None


def test_naive_chunk_covers_whole_file_with_overlap() -> None:
    text = "\n".join(f"line {i}" for i in range(300))
    chunks = naive_chunk_text("big.txt", text)
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 300
    # windows overlap, so consecutive chunks share some lines
    assert chunks[1].start_line < chunks[0].end_line


def test_naive_chunk_empty_file() -> None:
    assert naive_chunk_text("empty.txt", "") == []

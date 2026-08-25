from repolens.chunking.markdown import chunk_markdown_file

DOC = """\
# Title

Intro paragraph.

## Installation

Run pip install.

## Usage

Call the function.
"""


def test_markdown_splits_on_headings() -> None:
    chunks = chunk_markdown_file("README.md", DOC)
    headings = [c.symbol for c in chunks]
    assert "Title" in headings
    assert "Installation" in headings
    assert "Usage" in headings


def test_markdown_section_contains_its_body_not_the_next_sections() -> None:
    chunks = chunk_markdown_file("README.md", DOC)
    install_chunk = next(c for c in chunks if c.symbol == "Installation")
    assert "Run pip install" in install_chunk.text
    assert "Call the function" not in install_chunk.text


def test_markdown_empty_file() -> None:
    assert chunk_markdown_file("empty.md", "") == []

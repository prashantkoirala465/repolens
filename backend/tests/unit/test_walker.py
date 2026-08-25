from pathlib import Path

from repolens.chunking.walker import chunk_file, iter_indexable_files


def test_extensionless_readme_is_indexed(tmp_path: Path) -> None:
    (tmp_path / "README").write_text("Hello World!\n\nThis repo is an example.\n")

    files = iter_indexable_files(tmp_path)

    assert files == [tmp_path / "README"]


def test_extensionless_readme_is_chunked_as_markdown(tmp_path: Path) -> None:
    readme = tmp_path / "README"
    readme.write_text("Hello World!\n")

    chunks = chunk_file(tmp_path, readme)

    assert len(chunks) == 1
    assert "Hello World!" in chunks[0].text


def test_random_extensionless_file_is_not_indexed(tmp_path: Path) -> None:
    (tmp_path / "Makefile.rules").write_text("build:\n\techo hi\n")
    (tmp_path / "some_binary").write_bytes(b"\x00\x01\x02")

    files = iter_indexable_files(tmp_path)

    assert files == []

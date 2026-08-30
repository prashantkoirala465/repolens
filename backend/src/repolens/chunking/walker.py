"""Discovers and filters files worth indexing from a cloned repo checkout.

Bounds file count/size deliberately: an arbitrary public repo is untrusted
input, not just "more data to embed."
"""

from pathlib import Path

from repolens.chunking.base import Chunk
from repolens.chunking.code import chunk_code_file, language_for_path
from repolens.chunking.markdown import chunk_markdown_file
from repolens.core.config import get_settings

_SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".next",
    ".turbo",
    "vendor",
    "target",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}
_SKIP_FILE_SUFFIXES = {
    ".lock",
    ".min.js",
    ".min.css",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".db",
    ".sqlite",
    ".pyc",
    ".so",
    ".dylib",
    ".dll",
    ".wasm",
}
_MARKDOWN_SUFFIXES = {".md", ".mdx", ".rst"}
# Extensionless doc files are extremely common (octocat/Hello-World's entire
# content is a file literally named `README`, no suffix) — without this, a repo
# whose only content is prose files indexes zero chunks.
_EXTENSIONLESS_DOC_NAMES = {
    "readme",
    "license",
    "licence",
    "contributing",
    "changelog",
    "authors",
    "notice",
    "code_of_conduct",
    "security",
}


def _is_extensionless_doc(path: Path) -> bool:
    return path.suffix == "" and path.stem.lower() in _EXTENSIONLESS_DOC_NAMES


def iter_indexable_files(repo_root: Path) -> list[Path]:
    settings = get_settings()
    max_file_bytes = settings.max_file_size_kb * 1024
    files: list[Path] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.relative_to(repo_root).parts[:-1]):
            continue
        if path.suffix.lower() in _SKIP_FILE_SUFFIXES:
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
        except OSError:
            continue
        is_code = language_for_path(str(path)) is not None
        is_markdown = path.suffix.lower() in _MARKDOWN_SUFFIXES or _is_extensionless_doc(path)
        if not is_code and not is_markdown:
            continue
        files.append(path)
        if len(files) >= settings.max_files_indexed:
            break

    return files


def chunk_file(repo_root: Path, path: Path) -> list[Chunk]:
    relative_path = str(path.relative_to(repo_root))
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    if path.suffix.lower() in _MARKDOWN_SUFFIXES or _is_extensionless_doc(path):
        return chunk_markdown_file(relative_path, text)
    return chunk_code_file(relative_path, text)

"""AST-aware code chunking via tree-sitter.

Naive fixed-width chunking splits functions mid-body and drops the
enclosing class/import context a reader needs to make sense of a snippet.
Walking the AST and emitting whole top-level definitions avoids that at
the cost of supporting a fixed, explicit set of languages — anything else
falls back to `naive_chunk_text`, which is a known-worse but always-safe
default (see docs/adr/0003).
"""

from pathlib import Path

import tree_sitter_go
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from repolens.chunking.base import Chunk, ChunkKind

# Node types, per language, that should become their own top-level chunk.
_DEFINITION_NODE_TYPES: dict[str, set[str]] = {
    "python": {"function_definition", "class_definition"},
    "javascript": {"function_declaration", "class_declaration", "method_definition"},
    "typescript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "interface_declaration",
    },
    "go": {"function_declaration", "method_declaration", "type_declaration"},
}

_EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
}

_LANGUAGES: dict[str, Language] = {
    "python": Language(tree_sitter_python.language()),
    "javascript": Language(tree_sitter_javascript.language()),
    "typescript": Language(tree_sitter_typescript.language_typescript()),
    "go": Language(tree_sitter_go.language()),
}

NAIVE_WINDOW_LINES = 120
NAIVE_OVERLAP_LINES = 15


def language_for_path(file_path: str) -> str | None:
    return _EXTENSION_LANGUAGE.get(Path(file_path).suffix.lower())


def _symbol_name(node: Node, source: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    return source[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")


def _top_level_definitions(root: Node, definition_types: set[str]) -> list[Node]:
    """Only top-level (module/class-body) definitions — nested functions stay
    inside their parent's chunk rather than fragmenting it further."""
    matches: list[Node] = []
    for child in root.children:
        if child.type in definition_types or child.type in {"decorated_definition"}:
            matches.append(child)
        elif child.type in {"export_statement"}:
            inner = next((c for c in child.children if c.type in definition_types), None)
            if inner is not None:
                matches.append(child)
    return matches


def chunk_code_file(file_path: str, text: str) -> list[Chunk]:
    language_name = language_for_path(file_path)
    if language_name is None:
        return naive_chunk_text(file_path, text)

    try:
        parser = Parser(_LANGUAGES[language_name])
        source = text.encode("utf-8")
        tree = parser.parse(source)
    except Exception:
        return naive_chunk_text(file_path, text)

    definitions = _top_level_definitions(tree.root_node, _DEFINITION_NODE_TYPES[language_name])
    if not definitions:
        return naive_chunk_text(file_path, text)

    chunks: list[Chunk] = []
    covered_lines: set[int] = set()
    for node in definitions:
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        symbol = _symbol_name(node, source)
        chunks.append(
            Chunk(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                text=source[node.start_byte : node.end_byte].decode("utf-8", errors="replace"),
                kind=ChunkKind.CODE,
                symbol=symbol,
            )
        )
        covered_lines.update(range(start_line, end_line + 1))

    # Module-level code outside any definition (imports, constants, top-level
    # calls) still matters for retrieval — group the uncovered lines into a
    # single "module preamble" chunk rather than dropping them.
    lines = text.splitlines()
    preamble_lines = [
        i + 1 for i in range(len(lines)) if (i + 1) not in covered_lines and lines[i].strip()
    ]
    if preamble_lines:
        chunks.append(
            Chunk(
                file_path=file_path,
                start_line=min(preamble_lines),
                end_line=max(preamble_lines),
                text="\n".join(lines[i - 1] for i in preamble_lines),
                kind=ChunkKind.CODE,
                symbol=None,
            )
        )

    return sorted(chunks, key=lambda c: c.start_line)


def naive_chunk_text(file_path: str, text: str) -> list[Chunk]:
    """Fixed-window fallback for unsupported languages or parse failures.
    Deliberately worse than AST chunking — see docs/adr/0003 for the
    before/after eval-harness numbers this tradeoff was measured against."""
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[Chunk] = []
    start = 0
    step = NAIVE_WINDOW_LINES - NAIVE_OVERLAP_LINES
    while start < len(lines):
        end = min(start + NAIVE_WINDOW_LINES, len(lines))
        chunk_text = "\n".join(lines[start:end])
        if chunk_text.strip():
            chunks.append(
                Chunk(
                    file_path=file_path,
                    start_line=start + 1,
                    end_line=end,
                    text=chunk_text,
                    kind=ChunkKind.CODE,
                    symbol=None,
                )
            )
        if end == len(lines):
            break
        start += step
    return chunks

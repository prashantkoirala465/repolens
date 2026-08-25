"""Heading-aware chunking for Markdown/docs: split on ATX headings (`#`..`######`)
so each chunk is one coherent section instead of an arbitrary character window."""

import re

from repolens.chunking.base import Chunk, ChunkKind

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def chunk_markdown_file(file_path: str, text: str) -> list[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []

    sections: list[tuple[int, str | None, list[str]]] = [(1, None, [])]
    for i, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match:
            sections.append((i + 1, match.group(2).strip(), []))
        sections[-1][2].append(line)

    chunks: list[Chunk] = []
    for start_line, heading, section_lines in sections:
        body = "\n".join(section_lines)
        if not body.strip():
            continue
        chunks.append(
            Chunk(
                file_path=file_path,
                start_line=start_line,
                end_line=start_line + len(section_lines) - 1,
                text=body,
                kind=ChunkKind.DOC,
                symbol=heading,
            )
        )
    return chunks

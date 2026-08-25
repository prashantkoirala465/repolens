from dataclasses import dataclass
from enum import StrEnum


class ChunkKind(StrEnum):
    CODE = "code"
    DOC = "doc"


@dataclass(frozen=True, slots=True)
class Chunk:
    """A self-contained, citable unit of a repo: one function, one doc section, etc."""

    file_path: str
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive
    text: str
    kind: ChunkKind
    symbol: str | None = None  # function/class name, or doc heading

    @property
    def chunk_id(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"

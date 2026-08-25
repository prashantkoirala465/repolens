import uuid

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    symbol: str | None
    score: float
    cited: bool


class QueryResponse(BaseModel):
    query_id: uuid.UUID
    answer: str
    retrieved_chunks: list[RetrievedChunkResponse]
    rejected_citation_count: int

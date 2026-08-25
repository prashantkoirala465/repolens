import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class IndexStatus(enum.StrEnum):
    QUEUED = "queued"
    CLONING = "cloning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(128), nullable=False, default="main")
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[IndexStatus] = mapped_column(
        # values_callable: SQLAlchemy's Enum type stores the member .name ("QUEUED")
        # by default, but the Postgres enum type (alembic/versions/0001) only has the
        # lowercase .value labels ("queued", ...) — without this, every insert fails
        # with InvalidTextRepresentationError.
        Enum(IndexStatus, name="index_status", values_callable=lambda cls: [e.value for e in cls]),
        nullable=False,
        default=IndexStatus.QUEUED,
    )
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    queries: Mapped[list["Query"]] = relationship(
        back_populates="repo", cascade="all, delete-orphan"
    )


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    cited_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    rejected_citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repo: Mapped["Repo"] = relationship(back_populates="queries")

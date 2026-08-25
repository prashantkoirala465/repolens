"""initial schema: repos, queries

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_INDEX_STATUS = postgresql.ENUM(
    "queued", "cloning", "chunking", "embedding", "ready", "failed", name="index_status"
)


def upgrade() -> None:
    # Least-privilege runtime role: the app connects as repolens_app, which gets
    # no DDL rights, only DML on the tables this migration creates. Only the
    # migration role (MIGRATION_DATABASE_URL) can ever alter the schema.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'repolens_app') THEN
                CREATE ROLE repolens_app LOGIN PASSWORD 'repolens_app';
            END IF;
        END
        $$;
        """
    )

    # No explicit _INDEX_STATUS.create() here: op.create_table below emits its own
    # CREATE TYPE for the enum column, and calling both raises DuplicateObjectError.
    op.create_table(
        "repos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("github_url", sa.String(512), nullable=False, unique=True),
        sa.Column("owner", sa.String(256), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("default_branch", sa.String(128), nullable=False, server_default="main"),
        sa.Column("commit_sha", sa.String(40), nullable=True),
        sa.Column("status", _INDEX_STATUS, nullable=False, server_default="queued"),
        sa.Column("status_detail", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("retrieved_chunk_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("cited_chunk_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("rejected_citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_queries_repo_id", "queries", ["repo_id"])

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON repos, queries TO repolens_app")
    op.execute("GRANT USAGE ON SCHEMA public TO repolens_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON repos, queries FROM repolens_app")
    op.drop_index("ix_queries_repo_id", table_name="queries")
    op.drop_table("queries")
    op.drop_table("repos")
    _INDEX_STATUS.drop(op.get_bind())

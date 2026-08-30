# RepoLens

[![CI](https://github.com/prashantkoirala465/repolens/actions/workflows/ci.yml/badge.svg)](https://github.com/prashantkoirala465/repolens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Ask questions about any public GitHub repo and get answers cited to the exact
file and line range they came from. Same category as Sourcegraph Cody's `ask`
or Cursor's `@codebase` — the difference is that retrieval quality here is
something you can measure, not something you have to take on faith.

**Status:** Phase 1 of 5 complete — clone → chunk → embed → index → query →
cited answer works end to end, with unit tests and CI green on every push.
The eval harness (Phase 2, the actual point of this project) is next; see
[Roadmap](#roadmap).

## The problem

Every RAG demo answers questions. Almost none of them tell you whether the
answers are backed by the right source material or by something that merely
shares vocabulary with the question. That gap is invisible until it isn't —
usually in front of the person you built the thing for. RepoLens is built
around treating retrieval quality as a number you track, not a property you
assume.

## What it does

1. Paste a public GitHub repo URL.
2. It's shallow-cloned, walked, and chunked — code by AST (tree-sitter, so a
   chunk is always a complete function/class, never a truncated fragment),
   docs by heading.
3. Chunks are embedded and indexed into Qdrant — locally via Ollama by
   default (free, no API key), or Voyage's code-specialized model if you
   opt into the cloud path.
4. Ask a question. The answer is generated only from retrieved chunks, and
   every citation is checked server-side against what was actually retrieved
   before the response goes out — see [Security](#security).

```mermaid
flowchart LR
    UI[Next.js frontend] -->|REST| API[FastAPI]
    API -->|enqueue| Q[(Redis)]
    Q --> W[arq worker]
    W -->|clone + parse| GH[GitHub]
    W -->|chunk: tree-sitter / heading-aware| CH[Chunker]
    CH -->|embed: Ollama or Voyage| VDB[(Qdrant)]
    API -->|hybrid search| VDB
    API -->|generate w/ citations| LLM[Ollama or Claude]
    API --> PG[(Postgres)]
```

## Design decisions

The non-obvious calls — and why — are written down as ADRs rather than left
to be reverse-engineered from the diff:

- [0001](docs/adr/0001-embeddings-voyage-code-3.md) — embeddings: Voyage
  `voyage-code-3` over OpenAI, on code-retrieval benchmark performance
- [0002](docs/adr/0002-vector-store-qdrant-over-pgvector.md) — vector store:
  Qdrant over pgvector, because hybrid search is core to the product
- [0003](docs/adr/0003-chunking-ast-aware-over-fixed-width.md) — chunking:
  AST-aware over fixed-width, with naive chunking as an explicit fallback
- [0004](docs/adr/0004-task-queue-arq.md) — task queue: arq
- [0005](docs/adr/0005-citation-validation-as-prompt-injection-defense.md) —
  citation validation as the actual prompt-injection defense
- [0006](docs/adr/0006-local-model-support-via-ollama.md) — local models
  (Ollama) as the default provider, cloud as opt-in

## API surface

| Method | Path                | Description                                |
| ------ | ------------------- | ------------------------------------------- |
| POST   | `/repos`             | Index a repo (idempotent per `github_url`) |
| GET    | `/repos/{id}`        | Poll indexing status                       |
| POST   | `/repos/{id}/query`  | Ask a question, get a cited answer         |
| GET    | `/health`            | Liveness                                   |

## Getting started

### Prerequisites

- Docker and Docker Compose
- [Ollama](https://ollama.com), running on the host — the default provider
  path doesn't use any cloud API, but it does need Ollama installed
  natively (not in Docker; see [ADR-0006](docs/adr/0006-local-model-support-via-ollama.md)
  for why)

### Quickstart

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
cp .env.example .env
docker compose up
```

The API comes up on `:8000`, the frontend on `:3000`. Postgres/Redis/Qdrant
are health-checked and the app services wait on them before starting.

Want better retrieval/answer quality and don't mind paying for it? Set
`EMBEDDING_PROVIDER=voyage` and/or `GENERATION_PROVIDER=anthropic` in `.env`
and fill in the matching API key — everything else stays the same.

### Development

Running the backend and frontend directly (against the Postgres/Redis/Qdrant
containers, without rebuilding a Docker image on every change):

```bash
# backend — needs uv (https://docs.astral.sh/uv/)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn repolens.main:app --reload

# frontend — needs pnpm
cd frontend
pnpm install
pnpm dev
```

Checks that run in CI, runnable locally the same way:

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -v

cd frontend
pnpm run lint
pnpm run test
pnpm run build
```

Backend integration tests (`tests/integration`) run against real
Postgres/Redis/Qdrant service containers; they're wired into `ci.yml` but
currently gated off (`if: false`) pending the Phase 1 integration suite.

## Project layout

```
backend/src/repolens/
├── api/routes/     # FastAPI routers: repos, query, health
├── chunking/       # tree-sitter AST chunking + fallback, markdown chunking
├── embeddings/      # Embedder protocol, Ollama + Voyage implementations
├── generation/      # Generator protocol, Ollama + Anthropic, citation validation
├── retrieval/       # Qdrant collection management and search
├── services/        # git cloning, the indexing pipeline
├── workers/         # arq worker entrypoint and task
└── db/              # SQLAlchemy models, session

frontend/src/
├── app/             # Next.js routes: repo submission, repo workspace
├── components/      # RepoForm, QueryPanel, RetrievalInspector, StatusBadge
└── lib/             # API client, TanStack Query provider
```

## Security

Indexing an arbitrary public repo means untrusted code and text flows through
the pipeline. What's bounded, and how:

- **Resource limits at index time** — max repo size, max file size, clone
  timeout, max files per repo (`services/git.py`, `chunking/walker.py`). No
  repo content is ever executed; tree-sitter only parses.
- **Prompt injection at query time** — a malicious README could contain text
  aimed at whatever eventually reads it. Retrieved chunks are framed as data,
  never as instructions, in the system prompt. More importantly, every
  citation the model emits is checked against the actual retrieved set before
  the response returns — see ADR-0005. The practical effect: an injected
  instruction can make the model say something wrong, but it can't forge
  evidence for a claim and there's no action surface for it to abuse.
- **CI security scanning** — `gitleaks` on every push/PR for committed
  secrets, `pip-audit` against the resolved backend dependency set.

## Roadmap

- **Eval harness (Phase 2)** — a hand-labeled benchmark (LLM-drafted
  candidates, human-verified) with precision@k/recall@k/MRR/nDCG, and an
  `eval diff` CLI to compare retrieval strategies with real numbers instead of
  assertions.
- **Hybrid retrieval (Phase 3)** — BM25 + dense fusion via Qdrant's Query API,
  measured against the Phase 1 baseline through the eval harness before it's
  called an improvement.
- **Hardening (Phase 4)** — rate limiting, structured observability, the
  currently-disabled integration suite turned on in CI.
- Not planned: multi-tenant auth, private-repo support. This is a portfolio
  piece about retrieval quality, not a hosted product.

## License

MIT — see [LICENSE](LICENSE).

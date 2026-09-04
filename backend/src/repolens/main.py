from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from repolens.api.routes import health, query, repos
from repolens.core.config import get_settings
from repolens.core.logging import configure_logging
from repolens.core.middleware import RequestContextMiddleware
from repolens.core.rate_limit import limiter

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="RepoLens",
    description="RAG search over any public GitHub repo, with a real eval harness.",
)

app.state.limiter = limiter
# slowapi's handler is typed narrowly for RateLimitExceeded; Starlette's stub
# wants a general Exception handler — a known slowapi/mypy mismatch, not a
# real type error.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# The frontend runs on a different origin (Next.js dev server / a separate
# deployed host) than this API, so browser requests need CORS explicitly
# enabled — see CORS_ORIGINS in .env.example.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# add_middleware inserts at the front of Starlette's middleware list, and
# the front ends up outermost — added last, this wraps everything above it
# (CORS, rate limiting), so even a 429 or a CORS-rejected request gets a
# request_id and an access log line.
app.add_middleware(RequestContextMiddleware)

app.include_router(health.router)
app.include_router(repos.router)
app.include_router(query.router)

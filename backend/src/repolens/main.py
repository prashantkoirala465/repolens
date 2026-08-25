from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repolens.api.routes import health, query, repos
from repolens.core.config import get_settings
from repolens.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="RepoLens",
    description="RAG search over any public GitHub repo, with a real eval harness.",
)

# The frontend runs on a different origin (Next.js dev server / a separate
# deployed host) than this API, so browser requests need CORS explicitly
# enabled — see CORS_ORIGINS in .env.example.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(repos.router)
app.include_router(query.router)

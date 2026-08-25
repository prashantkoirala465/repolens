from fastapi import FastAPI

from repolens.api.routes import health, query, repos
from repolens.core.config import get_settings
from repolens.core.logging import configure_logging

configure_logging(get_settings().log_level)

app = FastAPI(
    title="RepoLens",
    description="RAG search over any public GitHub repo, with a real eval harness.",
)

app.include_router(health.router)
app.include_router(repos.router)
app.include_router(query.router)

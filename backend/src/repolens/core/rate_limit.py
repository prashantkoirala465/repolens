"""Redis-backed rate limiting for the two routes with real compute/cost
behind them — POST /repos triggers a clone + embed job, POST .../query
triggers generation. GET routes stay unlimited.

Redis is already a deployed dependency (arq's job queue); reusing it as the
rate-limit store means no new infrastructure, and it's correct in a way
in-memory storage isn't once there's more than one uvicorn worker process.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from repolens.core.config import get_settings

_settings = get_settings()

limiter = Limiter(key_func=get_remote_address, storage_uri=_settings.redis_url)

REPOS_RATE_LIMIT = _settings.rate_limit_repos
QUERY_RATE_LIMIT = _settings.rate_limit_query

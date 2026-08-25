from typing import Any

from arq.connections import RedisSettings

from repolens.core.config import get_settings
from repolens.core.logging import configure_logging
from repolens.workers.tasks import index_repo_task


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging(get_settings().log_level)


class WorkerSettings:
    functions = [index_repo_task]
    redis_settings = _redis_settings()
    on_startup = startup
    max_jobs = 4
    job_timeout = 300

"""Clones a benchmark repo at an exact, pinned commit.

`services/git.shallow_clone` is deliberately HEAD-only: it's built for
arbitrary, untrusted, user-submitted repos, where "whatever's on the default
branch right now" is the only thing that makes sense. A benchmark's
hand-labeled line numbers describe one specific commit forever, so eval
needs to fetch a commit that isn't necessarily HEAD. GitHub allows fetching
any reachable SHA directly, so an empty repo plus a scoped
`git fetch --depth 1 origin <sha>` gets there without pulling full history.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from repolens.core.config import get_settings
from repolens.services.git import CloneTimeoutError, ParsedRepo


def checkout_at_commit(parsed: ParsedRepo, commit: str) -> Path:
    settings = get_settings()
    dest = Path(tempfile.mkdtemp(prefix=f"repolens-eval-{parsed.owner}-{parsed.name}-"))
    commands = [
        ["git", "init", "--quiet", str(dest)],
        ["git", "-C", str(dest), "remote", "add", "origin", parsed.clone_url],
        ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", commit],
        ["git", "-C", str(dest), "checkout", "--quiet", "FETCH_HEAD"],
    ]
    try:
        for command in commands:
            subprocess.run(
                command, check=True, timeout=settings.clone_timeout_s, capture_output=True
            )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneTimeoutError(
            f"checkout of {parsed.clone_url}@{commit} exceeded {settings.clone_timeout_s}s"
        ) from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise ValueError(
            f"failed to check out {parsed.clone_url}@{commit}: "
            f"{exc.stderr.decode(errors='replace')}"
        ) from exc

    return dest

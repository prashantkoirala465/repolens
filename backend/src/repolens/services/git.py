"""Shallow-clones an untrusted public repo into a scratch directory.

Threat model: the URL and its content are user-supplied and untrusted. We
only ever shell out to `git clone --depth 1`, never execute
anything from inside the checkout, bound the clone with a timeout, and cap
the resulting tree size after the fact (git has no built-in "abort if the
repo is too big" flag for a shallow clone).
"""

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from repolens.core.config import get_settings

_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<name>[\w.-]+?)(?:\.git)?/?$"
)


class InvalidRepoUrlError(ValueError):
    pass


class RepoTooLargeError(RuntimeError):
    pass


class CloneTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedRepo:
    owner: str
    name: str
    clone_url: str


def parse_github_url(url: str) -> ParsedRepo:
    match = _GITHUB_URL_RE.match(url.strip())
    if not match:
        raise InvalidRepoUrlError(f"not a github.com repo URL: {url!r}")
    clone_url = f"https://github.com/{match['owner']}/{match['name']}.git"
    return ParsedRepo(owner=match["owner"], name=match["name"], clone_url=clone_url)


def _dir_size_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def shallow_clone(parsed: ParsedRepo) -> Path:
    settings = get_settings()
    dest = Path(tempfile.mkdtemp(prefix=f"repolens-{parsed.owner}-{parsed.name}-"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", parsed.clone_url, str(dest)],
            check=True,
            timeout=settings.clone_timeout_s,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneTimeoutError(
            f"clone of {parsed.clone_url} exceeded {settings.clone_timeout_s}s"
        ) from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise ValueError(f"git clone failed: {exc.stderr.decode(errors='replace')}") from exc

    size_bytes = _dir_size_bytes(dest)
    max_bytes = settings.max_repo_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        shutil.rmtree(dest, ignore_errors=True)
        raise RepoTooLargeError(
            f"{parsed.owner}/{parsed.name} is {size_bytes / 1_048_576:.0f}MB, "
            f"over the {settings.max_repo_size_mb}MB limit"
        )

    return dest


def current_commit_sha(repo_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def cleanup(repo_dir: Path) -> None:
    shutil.rmtree(repo_dir, ignore_errors=True)

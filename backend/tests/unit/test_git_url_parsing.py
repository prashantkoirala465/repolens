import pytest

from repolens.services.git import InvalidRepoUrlError, parse_github_url


def test_parses_plain_github_url() -> None:
    parsed = parse_github_url("https://github.com/psf/requests")
    assert parsed.owner == "psf"
    assert parsed.name == "requests"
    assert parsed.clone_url == "https://github.com/psf/requests.git"


def test_parses_url_with_git_suffix_and_trailing_slash() -> None:
    parsed = parse_github_url("https://github.com/psf/requests.git/")
    assert parsed.name == "requests"


@pytest.mark.parametrize(
    "url",
    [
        "not a url",
        "https://gitlab.com/psf/requests",
        "https://github.com/psf",
        "git@github.com:psf/requests.git",
    ],
)
def test_rejects_non_github_urls(url: str) -> None:
    with pytest.raises(InvalidRepoUrlError):
        parse_github_url(url)

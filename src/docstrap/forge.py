"""The boundary a source-control provider sits behind.

Docstrap is an integrator: it drives other people's tools rather than
reimplementing them. Source control is one such tool, and **GitHub is
one provider among several intended, not the assumption**. Git support
is headed for a plugin — `pluggy` is the likely mechanism — and this
module is the seam that plugin will register into.

It is deliberately *not* a plugin system, and it is deliberately small,
because **docstrap does not create repositories**. The user creates the
store's repository under their own account, on the service they chose,
under the name they chose, and hands docstrap the URL and the
credentials. That act is the explicit choice; nothing here reaches a
hosting service on its own initiative, so there is no API client, no
CLI to shell out to, and no token for this module to hold.

What is left is the two things that are genuinely provider-specific and
purely textual:

1. the URL a repository of a given name **would** have, which docstrap
   offers as a *suggestion* while the user is choosing a name, and
2. whether two URLs address one repository, so a remote spelled `https`
   is not rewritten to `ssh` on every run.

A second provider is a second class implementing :class:`Forge`, and the
callers above it do not change.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class ForgeError(RuntimeError):
    """Raised when a source-control provider cannot answer."""


@runtime_checkable
class Forge(Protocol):
    """A source-control provider docstrap knows how to address."""

    #: Short name this provider is selected by.
    name: str

    def suggested_url(self, owner: str, repository: str, https: bool = False) -> str:
        """The URL a repository of this name would have. A suggestion only."""
        ...

    def same_repository(self, left: str, right: str) -> bool:
        """True when two git URLs address one repository on this provider."""
        ...


class GitHubForge:
    """GitHub URL shapes. Nothing here talks to GitHub.

    Creating the repository is the user's, so this class has no client,
    no credentials and no network call — only the two textual questions
    the protocol asks.
    """

    name = "github"

    #: URL prefixes that address github.com, longest-first so the ssh
    #: form is not mistaken for a bare path.
    _PREFIXES = (
        "ssh://git@github.com/",
        "https://github.com/",
        "http://github.com/",
        "git://github.com/",
        "git@github.com:",
    )

    def suggested_url(self, owner: str, repository: str, https: bool = False) -> str:
        if https:
            return f"https://github.com/{owner}/{repository}.git"
        return f"git@github.com:{owner}/{repository}.git"

    def same_repository(self, left: str, right: str) -> bool:
        return self._identity(left) == self._identity(right)

    def _identity(self, url: str) -> str:
        """The owner/name two spellings of one repository share.

        `git@github.com:owner/name.git` and `https://github.com/owner/name`
        are the same place; a store already pointed at one must not be
        rewritten to the other on every run because the spelling differs.
        """
        text = url.strip().rstrip("/")
        if text.endswith(".git"):
            text = text[: -len(".git")]
        for prefix in self._PREFIXES:
            if text.startswith(prefix):
                return text[len(prefix):].lower()
        return text.lower()


class PlainGitForge:
    """Any git remote docstrap has no provider knowledge of.

    A URL on a self-hosted git server, a Gitea instance, a path on
    another disk. It cannot suggest a URL — there is no host to suggest
    one on — and it compares remotes as text. Selecting it is how a user
    says "I chose a service you do not know about", which has to be an
    ordinary case rather than an error, because the user choosing the
    service is the whole model.
    """

    name = "git"

    def suggested_url(self, owner: str, repository: str, https: bool = False) -> str:
        raise ForgeError(
            "docstrap has no URL to suggest for a plain git remote — it does "
            "not know the host. Pass the URL of the repository you created."
        )

    def same_repository(self, left: str, right: str) -> bool:
        return left.strip().rstrip("/") == right.strip().rstrip("/")


#: Providers docstrap knows today. A pluggy hook will add to this rather
#: than replace it; the registry is the seam, not the mechanism.
_PROVIDERS: dict[str, type] = {
    GitHubForge.name: GitHubForge,
    PlainGitForge.name: PlainGitForge,
}

#: The provider used when a caller does not name one. It decides what a
#: suggested name looks like and nothing else — no repository is created
#: on it, and a user who chose another service passes `git` with a URL.
DEFAULT_PROVIDER = GitHubForge.name


def get(provider: str = DEFAULT_PROVIDER) -> Forge:
    """The source-control provider to address."""
    try:
        return _PROVIDERS[provider]()
    except KeyError:
        known = ", ".join(sorted(_PROVIDERS))
        raise ForgeError(
            f"unknown source-control provider {provider!r}; docstrap knows: {known}"
        ) from None

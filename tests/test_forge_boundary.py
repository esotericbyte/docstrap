"""The provider boundary: every hosting-provider specific lives in `forge.py`.

A second provider is a second class implementing the same protocol, so
nothing above `forge` may name one. These lived beside the store's git
tests until promdance, and the store's git with it, moved out of this
package; promdance's suite holds the same fingerprints over its own
modules.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap import forge, paths


# --- the provider boundary ---------------------------------------------------


PACKAGE = Path(paths.__file__).parent


def _sources() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


#: Strings that only a module that knows a specific hosting provider has
#: any business containing. Each is verified below to be present in
#: `forge.py` itself, so none of them can pass vacuously.
PROVIDER_FINGERPRINTS = ("github.com", "git@github")


def test_the_provider_fingerprints_are_real():
    """The guard below is only worth anything if it can fail."""
    forge_source = PACKAGE / "forge.py"
    for fingerprint in PROVIDER_FINGERPRINTS:
        assert _in_code(forge_source, fingerprint), fingerprint


@pytest.mark.parametrize("fingerprint", PROVIDER_FINGERPRINTS)
def test_only_the_forge_module_knows_about_a_hosting_provider(fingerprint: str):
    """Git support is headed for a plugin; there is nothing to retrofit.

    Every provider specific lives in `forge.py`. A second provider is a
    second class implementing the same protocol, and no caller above it
    changes. Docstrings are exempt — naming GitHub in prose is not
    baking it in — so the check reads code lines only.
    """
    offenders = [
        path.name
        for path in _sources()
        if path.name != "forge.py" and _in_code(path, fingerprint)
    ]
    assert offenders == []


def _in_code(path: Path, fingerprint: str) -> bool:
    """True when the fingerprint appears outside docstrings and comments."""
    import ast
    import io
    import tokenize

    source = path.read_text(encoding="utf-8")
    if fingerprint not in source:
        return False
    docstrings: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            text = ast.get_docstring(node, clean=False)
            if text:
                docstrings.add(text)
    if any(fingerprint in text for text in docstrings):
        # Present in prose. Is it also present anywhere else?
        stripped = source
        for text in docstrings:
            stripped = stripped.replace(text, "")
        source = stripped
    lines = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            continue
        lines.append(token.string)
    return fingerprint in "".join(lines)


def test_the_forge_registry_is_a_seam_not_a_plugin_system():
    """Named, not built: reached by name, and extended by adding a class."""
    assert forge.DEFAULT_PROVIDER == "github"
    assert isinstance(forge.get(), forge.Forge)
    assert isinstance(forge.get("git"), forge.Forge)
    with pytest.raises(forge.ForgeError):
        forge.get("bitbucket")


def test_a_host_docstrap_knows_nothing_about_is_an_ordinary_case():
    """The user choosing the service is the model, so `git` is not an error."""
    plain = forge.get("git")
    assert plain.same_repository("ssh://me@box/srv/x.git", "ssh://me@box/srv/x.git/")
    with pytest.raises(forge.ForgeError, match="no URL to suggest"):
        plain.suggested_url("owner", "name")


def test_no_credential_or_network_machinery_is_carried_anywhere():
    """docstrap holds no keys: credentials for a push are git's own."""
    for path in _sources():
        text = path.read_text(encoding="utf-8")
        for fingerprint in ("requests", "urllib.request", "httpx", "GITHUB_TOKEN"):
            assert fingerprint not in text, (path.name, fingerprint)

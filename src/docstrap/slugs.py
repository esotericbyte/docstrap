"""The one slug function. Every slug docstrap writes down comes from here.

Docstrap used to carry two slugifiers — ``scan._slugify``, which
lowercased, and ``tools.derivatives.slugify``, which did not. A project
whose title was not already its slug therefore had two names, and
answers and reviews were written under the second one: a directory the
project never links to, so a submitted answer vanished without an error.
One function removes the class of defect rather than that instance of
it, so this module is the single owner and nothing else defines a slug.

**Normalisation is delegated to ``python-slugify``** (MIT, 8.x). Ours
adds exactly one rule the library has no opinion about, because it is
about docstrap's storage layout rather than about text:

    a path separator becomes ``__``

That rule is what keeps ``apps/review-app`` and ``apps`` distinguishable
as sibling directories under one promdance root, and it is why the
adoption is a wrapper rather than a bare re-export.

Stability matters more here than prettiness: these slugs are directory
names on disk that existing drafts already live under. The wrapper
reproduces the previous project-slug output for every ASCII input, so no
existing directory is renamed. Where it differs is where the old code
was wrong: non-ASCII text is now transliterated (``Café`` → ``cafe``)
instead of being left as a non-ASCII directory name, and input that
reduces to nothing yields ``unnamed`` instead of an empty string that
would silently resolve to the parent directory.
"""
from __future__ import annotations

from slugify import slugify as _slugify_text

#: What a ``/`` or ``\`` in a project path becomes in its slug.
PATH_SEPARATOR = "__"

#: Characters a slug may keep. Everything else collapses to a single
#: ``-``. Underscores are preserved so :data:`PATH_SEPARATOR` survives.
_KEEP = r"[^a-z0-9_-]+"

#: Used when the input reduces to nothing. Never an empty string: an
#: empty path component resolves to the parent directory.
UNNAMED = "unnamed"


def slugify(value: str) -> str:
    """Turn a path, a title or a document name into a docstrap slug.

    Idempotent — ``slugify(slugify(x)) == slugify(x)`` — which is what
    lets a caller that already holds a slug pass it through again
    without moving where it points.
    """
    text = value.replace("\\", "/").replace("/", PATH_SEPARATOR)
    return _slugify_text(text, regex_pattern=_KEEP, lowercase=True).strip("-_") or UNNAMED

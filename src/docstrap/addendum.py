"""The answer addendum — what the loop delivers.

A decision that leaves no artifact has been stored
rather than delivered, and three things already assumed otherwise —
documents as the unit of value, the documentation-first practice,
and a downstream contract stamp deriving from a document's hash so that an
answered question moves a version.

**One markdown file per answered document**, beside the original in
the project's draft root, at a stable path. Regenerated whole every time an answer is
submitted, so the file a person cites today is the same file tomorrow
and says what is true now. It is a derivative: the source document is
not touched — nothing is altered in place — which is why this is a file of its own rather
than a section appended to the question document.

**The version is a stamp over the answers.** ``answered_version`` in the
front-matter is a short digest of every answered question's key, prose
and submission time, in document order. It moves when, and only when, an
answer moves — a redraft that changes nothing leaves it alone, and a
submitted revision changes it. That is the property a downstream contract stamp
needs, and it is what "a version of the document recording that it was
answered" means here: a version *of the answered state*, recorded beside
the document, not a new column in the metadata database and not an edit
to the document itself.

**It is as current as the last submission.** Nothing regenerates it when
a question is renumbered or deleted in the source, because nothing tells
docstrap that happened; the next submission against that document
refreshes it whole. The front-matter carries ``generated_at`` so a reader
can see how old the statement is.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from docstrap import drafts, pairing
from docstrap.answers import AnswerStoreError
from docstrap.slugs import slugify

#: How the file is named. One per document, stable, so a citation keeps
#: working: `<doc-slug>__answers.md` beside the project's other drafts.
#: The doc slug goes through :func:`docstrap.slugs.slugify`, which turns a
#: nested pagename's separator into `__` — the one docstrap slug rule, and
#: the reason `a/b` and `a__b` cannot collide here by accident.
FILENAME_SUFFIX = "__answers.md"

#: Characters of the digest kept. Enough that two different answer sets
#: colliding is not a thing that happens; short enough to quote.
STAMP_LENGTH = 16


@dataclass(frozen=True)
class Addendum:
    """One delivered artifact, as it was written."""

    #: Where it is. This is the citation.
    path: Path
    #: The version of the answered state — see the module docstring.
    version: str
    document: str
    doc_slug: str
    doc_id: Optional[str]
    answered: int
    open: int
    generated_at: str

    def to_json(self) -> dict[str, object]:
        """What a surface or a consumer is told about the delivery."""
        return {
            "path": str(self.path),
            "version": self.version,
            "document": self.document,
            "docSlug": self.doc_slug,
            "docId": self.doc_id,
            "answered": self.answered,
            "open": self.open,
            "generatedAt": self.generated_at,
        }


def path_for(project_slug: str, doc_slug: str) -> Path:
    """Where a document's addendum lives: the project's draft root."""
    try:
        root = drafts.require(project_slug)
    except drafts.NoDraftRoot as exc:
        raise AnswerStoreError(str(exc)) from exc
    return root / f"{slugify(doc_slug)}{FILENAME_SUFFIX}"


def version_of(paired: pairing.Pairing) -> str:
    """The stamp over one document's answered state.

    Over **what was decided, and nothing else**: which questions have
    answers, and what those answers say.

    Three things are deliberately excluded, each because including it
    would move the version when no decision had moved.

    1. **The question's prose.** Rewording a question does not claim its
       answer changed.
    2. **The generation time.** Regenerating an unchanged document
       produces an unchanged version.
    3. **The submission time.** Pressing Finish again on text nobody
       edited is a re-affirmation, not a decision — and the store agrees,
       because it supersedes nothing in that case. A version
       that moved there would have a downstream consumer re-stamping a contract because
       someone clicked twice. This one was found by a real run, not by a
       test; the test that pins it now was written afterwards.

    Keys **are** included, so renumbering a question — which changes the
    key an answer hangs on — does move it, correctly: that
    answer now belongs to a different question.
    """
    material = [
        [pair.key, pair.answer_text] for pair in paired.pairs if pair.is_answered
    ]
    digest = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    return digest.hexdigest()[:STAMP_LENGTH]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render(paired: pairing.Pairing, *, version: str, generated_at: str) -> str:
    """The addendum's text for one document's pairing.

    Every question, answered or not, because the open ones are half of
    what a reader of this needs to know. An answer is reproduced as its
    author wrote it, in a block quote so the file reads as a record
    rather than as prose someone might edit.
    """
    documents = {pair.document for pair in paired.pairs}
    document = documents.pop() if len(documents) == 1 else (paired.doc_slug or "")
    doc_id = next((pair.doc_id for pair in paired.pairs if pair.doc_id), None)

    lines = [
        "---",
        f"answered_version: {json.dumps(version)}",
        f"document_id: {json.dumps(doc_id or '')}",
        f"doc_slug: {json.dumps(paired.doc_slug or '')}",
        f"answered: {paired.answered_count}",
        f"open: {paired.open_count}",
        f"generated_at: {json.dumps(generated_at)}",
        "---",
        "",
        f"# Answers — {document}",
        "",
        "Written by docstrap. This is a derivative "
        "beside the\ndocument, not an edit to it: "
        f"`{document}` still says exactly what its author wrote.",
        "",
        f"`answered_version` above is `{version}`. It is a digest of the answers "
        "below and\nmoves only when one of them does, so a consumer can tell "
        "whether a decision it\nacted on is still the decision.",
        "",
        f"{paired.answered_count} answered, {paired.open_count} open, "
        f"as of {generated_at}.",
        "",
    ]

    for pair in paired.pairs:
        lines.append(f"## {pair.question.label} — {pair.question.text}")
        lines.append("")
        if pair.is_answered:
            answer = pair.answer
            assert answer is not None
            stamped = answer.submitted_at or answer.answered_at
            by = f", {answer.answered_by}" if answer.answered_by else ""
            lines.append(f"**Answered** {stamped}{by}. Key `{pair.key}`.")
            if pair.superseded:
                lines.append("")
                lines.append(
                    f"Supersedes {pair.superseded} earlier answer"
                    f"{'' if pair.superseded == 1 else 's'}, kept in "
                    f"`answers-history.md`."
                )
            lines.append("")
            for line in pair.answer_text.splitlines() or [""]:
                lines.append(f"> {line}".rstrip())
        else:
            lines.append("**Open.** No answer has been submitted.")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def deliver(project_slug: str, doc_slug: str) -> Addendum:
    """Generate one document's addendum. The delivery, and the one path to it.

    Both writers call this after a submission — the qa tool and the
    qapanels instrument — for the same reason both write through
    :mod:`docstrap.answers`: one implementation, so the artifact cannot
    come out differently depending on which surface a person used.

    Raises :class:`docstrap.pairing.PairingError` if the project or the
    document cannot be resolved. A caller mid-submission should treat
    that as a failed delivery and say so, not as a failed answer: the
    answer is already stored.
    """
    paired = pairing.pair(project_slug, doc_slug)
    version = version_of(paired)
    generated_at = _now_iso()
    target = path_for(project_slug, doc_slug)
    target.write_text(
        render(paired, version=version, generated_at=generated_at), encoding="utf-8"
    )

    documents = {pair.document for pair in paired.pairs}
    return Addendum(
        path=target,
        version=version,
        document=documents.pop() if len(documents) == 1 else doc_slug,
        doc_slug=doc_slug,
        doc_id=next((pair.doc_id for pair in paired.pairs if pair.doc_id), None),
        answered=paired.answered_count,
        open=paired.open_count,
        generated_at=generated_at,
    )

"""Pairing a project's questions with their answers.

Named for what it does rather than for the domain: `docstrap.tools.qa` is
the answering FORM tool, and a `docstrap.qa` beside it would have been two
names one letter apart meaning different things.

Questions live in documents and are
found by scanning them; answers live in the keyed store. Neither module
knows about the other on purpose — :mod:`docstrap.questions` reads
``Q<n>`` labels and nothing else, and :mod:`docstrap.answers` is
emphatic that it is not an index of questions. **This is the one place
the two are put side by side**, and it is a module rather than a method
on either of them because it belongs to neither.

One pairing implementation, two projections. The qapanels instrument
serialises a pairing for *editing* — it needs a writer's unsubmitted
draft back — and the server's ``/api/answers`` serialises one for
*reading*, where a draft is precisely what must not appear. Those are
two deliberate views of one computation, which is a different thing from
two implementations of the pairing; a second scan-and-match would be the
defect the single-owner rules exist to prevent.

**The pairing introduces no index.** It is a scan, performed per call,
derived and disposable. Nothing caches it and nothing treats it as
authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from docstrap import answers as answer_store
from docstrap import metadata as meta
from docstrap import projectscope, questions


@dataclass(frozen=True)
class Pair:
    """One question and whatever answer it has, which may be none."""

    #: The document's slug within its project.
    doc_slug: str
    #: The document's path as a reader would cite it.
    document: str
    #: The metadata store's id for the document, or None if it has never
    #: been registered. Listing must not register one — answering is what
    #: does that — so an unanswered document in
    #: a project nobody has answered anything in has no id yet.
    doc_id: Optional[str]
    #: The question as the scan found it.
    question: questions.Question
    #: The answer the store holds for it, or None.
    answer: Optional[answer_store.Answer]
    #: How many earlier answers this question has had superseded.
    superseded: int = 0

    @property
    def key(self) -> Optional[str]:
        """``<doc-id>:<label>``, or None until the document has an id."""
        if self.doc_id is None:
            return None
        return answer_store.key_for(self.doc_id, self.question.label)

    @property
    def is_answered(self) -> bool:
        """Whether a person has submitted an answer to this question.

        A draft does not answer a question: an answer counts only once a
        person submits it, seen here from the reading side.
        """
        return self.answer is not None and self.answer.is_submitted

    @property
    def is_open(self) -> bool:
        return not self.is_answered

    @property
    def answer_text(self) -> str:
        """The submitted prose, or empty. Never a draft."""
        return self.answer.text if self.is_answered else ""


@dataclass(frozen=True)
class Pairing:
    """A project's questions paired with their answers, in scan order."""

    project: str
    title: str
    #: None for a project-wide pairing, the slug for a single document.
    doc_slug: Optional[str]
    pairs: tuple[Pair, ...]

    @property
    def count(self) -> int:
        return len(self.pairs)

    @property
    def open_count(self) -> int:
        return sum(1 for pair in self.pairs if pair.is_open)

    @property
    def answered_count(self) -> int:
        return self.count - self.open_count

    def by_document(self) -> Iterator[tuple[str, str, Optional[str], list[Pair]]]:
        """The pairs grouped by document, in the order they were scanned.

        Yields ``(doc_slug, document, doc_id, pairs)``. Grouping here
        rather than in each consumer keeps the two projections showing
        the same documents in the same order.
        """
        groups: dict[str, list[Pair]] = {}
        heads: dict[str, tuple[str, Optional[str]]] = {}
        for pair in self.pairs:
            if pair.doc_slug not in groups:
                heads[pair.doc_slug] = (pair.document, pair.doc_id)
                groups[pair.doc_slug] = []
            groups[pair.doc_slug].append(pair)
        for doc_slug, held in groups.items():
            document, doc_id = heads[doc_slug]
            yield doc_slug, document, doc_id, held


class PairingError(Exception):
    """The project, or a document within it, could not be resolved."""


def pair(project_slug: str, doc_slug: Optional[str] = None) -> Pairing:
    """Every question in scope, with whatever answer the store holds.

    ``doc_slug`` narrows the scan to one document. A slug the project
    does not declare raises rather than returning nothing, because
    nothing is indistinguishable from "this document poses no questions".
    """
    try:
        scope = projectscope.resolve_slug(project_slug)
    except projectscope.ScopeError as exc:
        raise PairingError(str(exc)) from exc

    if doc_slug is not None and scope.document_for_slug(doc_slug) is None:
        raise PairingError(
            f"{scope.slug} declares no document with the slug {doc_slug!r}"
        )

    held = {answer.key: answer for answer in answer_store.read(project_slug)}
    superseded: dict[str, int] = {}
    for entry in answer_store.history(project_slug):
        superseded[entry.key] = superseded.get(entry.key, 0) + 1

    found_pairs: list[Pair] = []
    for found in questions.scan(scope.documents()):
        slug = scope.document_slug(found.path)
        if slug is None:
            continue
        if doc_slug is not None and slug != doc_slug:
            continue
        # Read-only: pairing must not register a document in the
        # metadata store. Answering is what creates an id.
        registered = meta.get_document_by_path(str(found.path.resolve()))
        doc_id = registered.id if registered else None
        display = scope.display_path(found.path)
        for question in found.questions:
            key = f"{doc_id}:{question.label}" if doc_id else None
            answer = held.get(key) if key else None
            found_pairs.append(
                Pair(
                    doc_slug=slug,
                    document=display,
                    doc_id=doc_id,
                    question=question,
                    answer=answer,
                    superseded=superseded.get(key, 0) if key else 0,
                )
            )

    return Pairing(
        project=scope.slug,
        title=scope.title,
        doc_slug=doc_slug,
        pairs=tuple(found_pairs),
    )

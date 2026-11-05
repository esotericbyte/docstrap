"""The qapanels instrument's server routes.

Three routes, every path of them derived from the declaration — the
instrument writes no path down, here or in the browser.

``GET``   ``…/{project}/qa``              every question the project poses
``GET``   ``…/{project}/{doc_slug}/qa``   one document's questions
``POST``  ``…/{project}/qa``              record one answer, draft or
                                          submission, superseding any
                                          earlier answer to the same key
``POST``  ``…/{project}/{doc_slug}/qa``   say this document's answers are
                                          done

**The two GETs are the deliberate choice of scope.** The instrument registered only the project-wide
read, so opening it while reading one document listed every question in
the project; the fix is not to swap one default for another but to make
both reachable and say which is which. The panel defaults to the document
it was opened on, because that is what the reader is looking at, and
offers the project as the deliberate wider view.

Both prefixes come from :meth:`ToolDeclaration.server_route_prefixes`, so
the shape of a tool route is still written down in exactly one place.
``{doc_slug}`` there spans path separators, because a document's identity
IS a path below ``docs_root`` — ``proposals/0002-the-upgrade-path`` — and
flattening it into one segment was what made every nested document's
questions unreachable while blaming the server for it.

The two shapes still cannot capture each other, but that is now a checked
guarantee rather than an argument from segment counts: a project URL has
exactly one segment after the project and a document URL has two or more,
and :func:`docstrap.tools.declaration.check_route_separation` refuses at
mount time any route that reaches deeper than a base plus its collection.

The write stays on the project prefix alone. An answer's payload already
carries the document it answers, and the file it lands in is the
project's; a second writer path would be a second way to do one thing.

A sub-path under the project prefix is what none of these is, and that is
load-bearing. ``…/{project}/qa/answers`` is indistinguishable from the
document-targeted ``…/{project}/{doc_slug}/answers`` with ``doc_slug``
equal to ``qa``, and it matched the qa tool's endpoint instead of this
one — exactly the collision the declaration's derived prefixes exist to
make impossible. Now that the document parameter is greedy that is no
longer an argument about segment counts holding by luck; it is the
condition :func:`docstrap.tools.declaration.check_route_separation`
enforces on every declared route before the server starts.

The question listing is a **scan**, performed per request by
:func:`docstrap.pairing.pair` — the same reading ``docstrap questions`` does,
by the author's own ``Q<n>`` labels and by nothing else. It is derived
and disposable: nothing caches it and nothing treats it as
authoritative, which is what the answer key — a document id plus the
question's own label — was designed to keep.

This module does not pair questions with answers itself. It serialises
the pairing :mod:`docstrap.pairing` computes, in the EDITING projection: the
writer gets their own unsubmitted draft back. The server's
``/api/answers`` is the reading projection of the same pairing, and it
shows no draft at all.

Answers go through :mod:`docstrap.answers`, the one owner of the answer
file. This route is one of its writers; the qa tool and the task tool's
decisions route are the others.

A **submission** also delivers: :func:`docstrap.addendum.deliver`
regenerates the artifact beside the document that says what was decided.
Both writers call the one function, so the
artifact cannot come out differently depending on which surface a person
used. A draft delivers nothing, because a draft decides nothing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from docstrap import addendum, answers_done
from docstrap import answers as answer_store
from docstrap import pairing, projectscope
from docstrap.tools.declaration import Target, ToolDeclaration
from docstrap.tools.launcher import PageContext, resolve_alt_route


class AnswerSubmission(BaseModel):
    """What the editor panel sends — on an autosave, or on Finish.

    `doc_slug` and `label` are the two halves of the question's identity
    as the page knows it; the server turns them into the key. The answer
    text is markdown and is stored as written.

    `submitted` is what the Finish button sets, and it is the whole
    distinction between saving and answering: an autosave sends it false and
    stores a draft nothing downstream can see, and Finish sends it true.
    It defaults to false so that a stale bundle, or anything else that
    omits the field, writes a draft rather than silently deciding for a
    person that they were done.
    """

    doc_slug: str
    label: str
    answer: str
    submitted: bool = False
    answered_by: Optional[str] = None


def _scope(project: str) -> projectscope.ProjectScope:
    try:
        return projectscope.resolve_slug(project)
    except projectscope.ScopeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _document(scope: projectscope.ProjectScope, doc_slug: str) -> Path:
    found = scope.document_for_slug(doc_slug)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=f"{scope.slug} declares no document with the slug {doc_slug!r}",
        )
    return found


def _listing(
    project: str,
    only: Optional[str] = None,
    declaration: Optional[ToolDeclaration] = None,
) -> dict:
    """The questions in scope, each with whatever answer it has.

    **The editing projection** of :func:`docstrap.pairing.pair`. The server's
    ``/api/answers`` is the other one, and the difference between them is
    the point: this carries a writer's unsubmitted draft back to them,
    which is exactly what a consumer of decisions must not be shown. One
    pairing, two deliberate views — see :mod:`docstrap.pairing`.

    ``only`` narrows the scan to one document slug — the document scope.
    Both scopes return the same shape; what differs is how many documents
    come back, so a caller reading the result never has to know which one
    it asked for.
    """
    try:
        paired = pairing.pair(project, only)
    except pairing.PairingError as exc:
        # A slug the project does not declare is a 404, not an empty list
        # that would read as "this document poses no questions".
        raise HTTPException(status_code=404, detail=str(exc))

    # Where each document's "answers done" prompt posts, resolved here
    # like every other route the panel uses, or None for every document
    # when no command is configured — which is what hides the prompt.
    offered = declaration is not None and answers_done.configured_command() is not None

    documents = []
    for doc_slug, document, doc_id, pairs in paired.by_document():
        documents.append(
            {
                "docSlug": doc_slug,
                "path": document,
                "docId": doc_id,
                "questions": [_question(pair) for pair in pairs],
                "answersDoneRoute": (
                    resolve_alt_route(declaration, PageContext(paired.project, doc_slug))
                    if offered
                    else None
                ),
            }
        )

    return {
        "project": paired.project,
        "title": paired.title,
        "documents": documents,
        "count": paired.count,
        # Open means nobody has finished answering it. A draft is still
        # open, which is the distinction the Finish button bought and the
        # reason the panel's header could not count this before.
        "open": paired.open_count,
    }


def _deliver(project: str, doc_slug: str, submitted: bool) -> Optional[dict]:
    """Regenerate this document's answer addendum, if anything was decided.

    A submission is the delivery moment: the answer is stored and
    the artifact beside the document is rewritten to say so. A draft
    decides nothing and delivers nothing.

    A delivery that fails does **not** fail the request. The answer is
    already in the store at this point, and reporting the write as failed
    would invite a caller to retry a write that succeeded. The surface is
    told the delivery is absent and can say so.
    """
    if not submitted:
        return None
    try:
        return addendum.deliver(project, doc_slug).to_json()
    except (pairing.PairingError, OSError):
        return None


def _question(pair: pairing.Pair) -> dict:
    """One question as the editor needs it.

    `answer` is what goes in the textarea: the writer's own unfinished
    revision if they have one, the submitted answer otherwise.
    `submittedAnswer` is the decision, and it stays put while a revision
    is being typed over it.
    """
    answer = pair.answer
    return {
        "label": pair.question.label,
        "number": pair.question.number,
        "text": pair.question.text,
        "section": pair.question.section,
        "line": pair.question.line,
        "key": pair.key,
        "answer": answer.editable_text if answer else "",
        "submittedAnswer": pair.answer_text,
        "answeredAt": answer.answered_at if answer else None,
        "submitted": pair.is_answered,
        "submittedAt": answer.submitted_at if answer else None,
        "hasDraft": bool(answer and answer.has_draft),
        "draftedAt": answer.drafted_at if answer else None,
        "supersededCount": pair.superseded,
    }


def register(app, declaration: ToolDeclaration) -> tuple[str, ...]:
    """Mount the collection at both scopes, plus the write.

    Both prefixes are the declaration's; neither is written down here.
    The project scope is mounted first — it is the narrower pattern, and
    mounting the narrower one first is the habit that keeps a router
    reading top to bottom honest even though the two shapes are already
    disjoint by segment count (see
    :func:`docstrap.tools.declaration.check_route_separation`).
    """
    prefix, document_prefix = declaration.server_route_prefixes
    assert declaration.also_scoped_to is Target.DOCUMENT, (
        "qapanels declares the document scope as its second one"
    )

    @app.get(prefix)
    def list_questions(project: str) -> dict:
        """Project scope: every question the project's documents pose."""
        return _listing(project, declaration=declaration)

    @app.get(document_prefix)
    def list_document_questions(project: str, doc_slug: str) -> dict:
        """Document scope: the questions this one document poses.

        ``doc_slug`` arrives as the path it is — ``proposals/0002-the-
        upgrade-path`` — because that is what a document's identity is.
        A shape no document could have is a 404 like any other unknown
        slug; :func:`docstrap.projectscope.is_document_slug` says which
        shapes those are.
        """
        return _listing(project, only=doc_slug, declaration=declaration)

    @app.post(document_prefix)
    def answers_are_done(project: str, doc_slug: str) -> dict:
        """The "answers done" prompt: run the configured command once.

        Distinguished from the read by method, never by a sub-path. The
        command gets the project's slug and the document's path as the
        answer store records it, so the receiver finds the answers under
        the name they were written with. Whatever it said comes back
        here, success or its own error; there is no retry.
        """
        command = answers_done.configured_command()
        if command is None:
            raise HTTPException(
                status_code=404,
                detail="answers_done_command is not set in the user config",
            )
        scope = _scope(project)
        source = _document(scope, doc_slug)
        return answers_done.run(command, scope.slug, scope.display_path(source)).to_json()

    @app.post(prefix)
    def submit_answer(project: str, payload: AnswerSubmission) -> dict:
        scope = _scope(project)
        source = _document(scope, payload.doc_slug)
        doc_id = answer_store.document_id_for(source, project)
        try:
            stored = answer_store.put(
                project,
                doc_id=doc_id,
                label=payload.label,
                document=scope.display_path(source),
                text=payload.answer,
                submitted=payload.submitted,
                answered_by=payload.answered_by,
            )
        except answer_store.AnswerStoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {
            "key": stored.key,
            "docId": stored.doc_id,
            "label": stored.label,
            "answeredAt": stored.answered_at,
            "submitted": stored.is_submitted,
            "submittedAt": stored.submitted_at,
            "hasDraft": stored.has_draft,
            # How many earlier answers this question has had superseded.
            # The panel shows it; the point is that they are still there.
            "supersededCount": len(answer_store.history(project, stored.key)),
            "writtenTo": str(answer_store.store_path(project)),
            # The delivery, or None for a draft. A draft decides
            # nothing, so there is nothing to deliver yet.
            "addendum": _deliver(project, payload.doc_slug, payload.submitted),
        }

    return (prefix, document_prefix)

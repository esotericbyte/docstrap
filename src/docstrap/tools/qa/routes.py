"""The qa tool's server routes.

Mounted by :mod:`docstrap.tools.mounting`, which hands this module the
declaration. The path is not written here either: it comes from
``declaration.route_prefix``, derived from the tool's target and the
collection it declares it owns.

What this route does *not* own is the answer file. That belongs to
:mod:`docstrap.answers`, and this route is one
of its writers, the others being the qapanels instrument and the task
tool's decisions route. It used to
append a section per submission to a per-document file, which meant
answering the same question twice stacked two sections under one heading;
the question id in that file was decorative italic text rather than a key.
Now it writes a key, and writing a key twice supersedes.

Every submission also **delivers**: the answer addendum beside the
document is regenerated to say what was decided.
This tool has one control and it is a Submit button, so there is nothing
here that does not deliver.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from docstrap import addendum
from docstrap import answers as answer_store
from docstrap import pairing, projectscope
from docstrap.tools.declaration import ToolDeclaration


class AnswerSubmission(BaseModel):
    """Q&A tool POST body.

    `question_id` is the question's own label inside the document — the
    `:question-id:` the directive declares — and is the second half of the
    key the answer is stored under. `question` is the human-readable text,
    accepted for compatibility with what the form already sends and not
    stored: the answer store holds answers, not questions. `answer` is the
    user's text. `submitter` is optional.
    """

    question_id: str
    question: str = ""
    answer: str
    submitter: Optional[str] = None


def register(app, declaration: ToolDeclaration) -> tuple[str, ...]:
    """Mount the answers endpoint. Returns the paths mounted."""
    path = declaration.server_route_prefix
    assert path is not None, "qa declares an api_collection"

    @app.post(path)
    def submit_answer(project: str, doc_slug: str, payload: AnswerSubmission) -> dict:
        # The page told us its project slug and its doc slug; the scope is
        # what turns those back into the source document. A tool composes
        # no path of its own, here no more than in the browser.
        #
        # `doc_slug` is a PATH below the project's docs_root and arrives
        # spelled that way — `proposals/0002-the-upgrade-path`. Answering
        # a question in a nested document used to 405 here because the
        # route treated that identity as one segment.
        try:
            scope = projectscope.resolve_slug(project)
        except projectscope.ScopeError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        source = scope.document_for_slug(doc_slug)
        if source is None:
            raise HTTPException(
                status_code=404,
                detail=f"{project} declares no document with the slug {doc_slug!r}",
            )

        doc_id = answer_store.document_id_for(source, project)
        stored = answer_store.put(
            project,
            doc_id=doc_id,
            label=payload.question_id,
            document=scope.display_path(source),
            text=payload.answer,
            # This tool has one control and it is a Submit button: the
            # form posts nothing until a person presses it, so everything
            # arriving here is finished by construction. The qapanels
            # instrument is the one that also writes drafts.
            submitted=True,
            answered_by=payload.submitter,
        )
        # Everything arriving here is a submission, so everything here
        # delivers. One function, shared with the instrument, so the
        # artifact does not depend on which surface a person used.
        try:
            delivered = addendum.deliver(project, doc_slug).to_json()
        except (pairing.PairingError, OSError):
            # The answer is stored; only the artifact failed. Saying the
            # write failed would invite a retry of a write that worked.
            delivered = None

        return {
            "written_to": str(answer_store.store_path(project)),
            "question_id": payload.question_id,
            "key": stored.key,
            "answered_at": stored.answered_at,
            "submitted": stored.is_submitted,
            "submitted_at": stored.submitted_at,
            "addendum": delivered,
        }

    return (path,)

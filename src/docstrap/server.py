"""FastAPI app server: static site + JSON APIs.

Alpha 1 provided static serving only. Alpha 2 adds:

* /api/documents/<id>            — metadata GET/PATCH.
* /api/documents/<id>/state      — full document state (metadata read).
* /api/annotations               — W3C Web Annotation Protocol subset
                                   (GET list, POST create, PATCH, DELETE).
* /api/answers/<project>         — a project's questions paired with the
  /api/answers/<project>/<doc>     answers they have, read-only.

**The answers API is the server's, not a tool's.** The store has one
owner, :mod:`docstrap.answers`, and two tools write through it; a consumer asking what a project has decided should
not have to know which tool happens to exist, any more than it should
have to parse a markdown file. It is the same distinction metadata and
annotations already have — those are the server's too, and the tools
that use them mount their own collections elsewhere.

It is read-only here on purpose. Writing an answer means resolving a
document, creating its metadata id if it has none, and deciding whether
the write is a draft or a submission — all of which is a surface's job
and belongs where a person is answering.

On top of those, every declared tool's own routes are mounted from its
declaration by :mod:`docstrap.tools.mounting` — the qa tool's answers
endpoint and the review tool's reviews endpoint come from those tool
directories, and this module does not name their paths. Ask a
declaration for its ``route_prefix``.

Static site (the built aggregate) is mounted last, at /, so API routes
take precedence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from docstrap import annotations as ann
from docstrap import metadata as meta
from docstrap import pairing
from docstrap.tools import mounting


# --- request bodies ---------------------------------------------------------


class DocumentPatch(BaseModel):
    status: Optional[str] = None
    tags: Optional[list[str]] = None
    title: Optional[str] = None


class AnnotationCreate(BaseModel):
    body: Any
    target: Any
    motivation: Optional[str] = None
    creator: Optional[str] = None
    id: Optional[str] = None


class AnnotationPatch(BaseModel):
    body: Any = None
    target: Any = None
    motivation: Optional[str] = None


# --- helpers ---------------------------------------------------------------


#: What `?include=` accepts on the answers API.
_INCLUDE = ("all", "answered", "open")


def _answers_payload(project: str, doc_slug: Optional[str], include: str) -> dict:
    """The READING projection of :func:`docstrap.pairing.pair`.

    The qapanels instrument has the other one. The difference is that
    this shows **no draft, ever** — not its text, not that one exists.
    A consumer of this endpoint is acting on decisions, and an answer
    nobody has finished is not one; publishing unfinished text to an
    audience its author has not shown it to would be the reverse of what
    the Finish button is for.
    """
    if include not in _INCLUDE:
        raise HTTPException(
            status_code=400,
            detail=f"include must be one of {', '.join(_INCLUDE)}; got {include!r}",
        )
    try:
        paired = pairing.pair(project, doc_slug)
    except pairing.PairingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    items = []
    for pair in paired.pairs:
        if include == "answered" and not pair.is_answered:
            continue
        if include == "open" and pair.is_answered:
            continue
        answer = pair.answer if pair.is_answered else None
        items.append(
            {
                "key": pair.key,
                "docSlug": pair.doc_slug,
                "document": pair.document,
                "docId": pair.doc_id,
                "label": pair.question.label,
                "question": pair.question.text,
                "section": pair.question.section,
                "line": pair.question.line,
                "answered": pair.is_answered,
                "answer": pair.answer_text,
                "answeredAt": answer.answered_at if answer else None,
                "answeredBy": answer.answered_by if answer else None,
                "submittedAt": answer.submitted_at if answer else None,
                # How many earlier answers this question has had. They
                # are kept, and `answers-history.md` is where.
                "superseded": pair.superseded,
            }
        )

    return {
        "project": paired.project,
        "title": paired.title,
        "docSlug": paired.doc_slug,
        "include": include,
        "count": paired.count,
        "answered": paired.answered_count,
        "open": paired.open_count,
        "questions": items,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --- app factory -----------------------------------------------------------


def make_app(site_root: Path) -> FastAPI:
    app = FastAPI(title="docstrap")

    # --- /api/documents -----------------------------------------------------

    @app.get("/api/documents")
    def list_documents(project: Optional[str] = None) -> list[dict]:
        docs = meta.list_documents(project=project)
        return [
            {
                "id": d.id,
                "project": d.project,
                "current_path": d.current_path,
                "current_status": d.current_status,
                "title": d.title,
                "tags": d.tags,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
            }
            for d in docs
        ]

    @app.get("/api/documents/{doc_id}")
    def get_document(doc_id: str) -> dict:
        doc = meta.get_document_by_id(doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no such document: {doc_id}")
        return {
            "id": doc.id,
            "project": doc.project,
            "current_path": doc.current_path,
            "current_status": doc.current_status,
            "title": doc.title,
            "tags": doc.tags,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }

    @app.get("/api/documents/{doc_id}/state")
    def get_document_state(doc_id: str) -> dict:
        """Full state read — same as get_document today, kept as a separate
        endpoint so future extensions (git presence, dirty
        state, recent moves) have a stable home."""
        doc = meta.get_document_by_id(doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no such document: {doc_id}")
        return {
            "id": doc.id,
            "project": doc.project,
            "current_path": doc.current_path,
            "current_status": doc.current_status,
            "title": doc.title,
            "tags": doc.tags,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }

    @app.patch("/api/documents/{doc_id}")
    def patch_document(doc_id: str, patch: DocumentPatch) -> dict:
        doc = meta.get_document_by_id(doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no such document: {doc_id}")
        try:
            if patch.status is not None:
                doc = meta.set_status(doc_id, patch.status, source="user")
            if patch.tags is not None:
                doc = meta.set_tags(doc_id, patch.tags)
            # Title-only updates: touch documents.title directly since
            # metadata module doesn't have set_title() yet.
            if patch.title is not None and patch.tags is None and patch.status is None:
                with meta.connect() as conn:
                    conn.execute(
                        "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
                        (patch.title, _now_iso(), doc_id),
                    )
                doc = meta.get_document_by_id(doc_id)
        except meta.MetadataError as e:
            raise HTTPException(status_code=400, detail=str(e))
        assert doc is not None
        return {
            "id": doc.id,
            "project": doc.project,
            "current_path": doc.current_path,
            "current_status": doc.current_status,
            "title": doc.title,
            "tags": doc.tags,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }

    # --- /api/annotations ---------------------------------------------------

    @app.get("/api/annotations")
    def list_annotations(target: str) -> list[dict]:
        rows = ann.list_for_target(target)
        return [a.to_w3c() for a in rows]

    @app.post("/api/annotations")
    def create_annotation(payload: AnnotationCreate) -> dict:
        try:
            a = ann.create(
                body=payload.body,
                target=payload.target,
                motivation=payload.motivation,
                creator=payload.creator,
                annotation_id=payload.id,
            )
        except ann.AnnotationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return a.to_w3c()

    @app.patch("/api/annotations/{annotation_id:path}")
    def patch_annotation(annotation_id: str, payload: AnnotationPatch) -> dict:
        try:
            a = ann.update(
                annotation_id,
                body=payload.body,
                target=payload.target,
                motivation=payload.motivation,
            )
        except ann.AnnotationError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return a.to_w3c()

    @app.delete("/api/annotations/{annotation_id:path}")
    def delete_annotation(annotation_id: str) -> JSONResponse:
        removed = ann.delete(annotation_id)
        if not removed:
            raise HTTPException(status_code=404, detail=f"no such annotation: {annotation_id}")
        return JSONResponse(status_code=204, content=None)

    # --- /api/answers -------------------------------------------------------

    @app.get("/api/answers/{project}")
    def list_answers(project: str, include: str = "all") -> dict:
        """A project's questions, paired with the answers they have."""
        return _answers_payload(project, None, include)

    @app.get("/api/answers/{project}/{doc_slug:path}")
    def list_document_answers(
        project: str, doc_slug: str, include: str = "all"
    ) -> dict:
        """One document's questions, paired with the answers they have.

        ``doc_slug`` spans path separators because a document's identity
        is its path below ``docs_root`` — ``proposals/0002-the-upgrade-
        path``. The `answered` tool reads this on every page load, and
        while this was one segment it silently rendered no answers at all
        under any question in any nested document.

        The two shapes cannot capture each other: ``{project}`` is a
        single segment, so ``/api/answers/P`` reaches the project read
        above and only a URL with a further segment reaches this one.
        """
        return _answers_payload(project, doc_slug, include)

    # --- declared tool routes -----------------------------------------------
    #
    # The server knows no tool's URL. Each declaration derives its own
    # route prefix from its target and the collection it owns, and its
    # tool directory holds the handlers. Adding a tool that serves an
    # API changes nothing here.
    mounting.mount_all(app)

    # --- static site (mounted last so /api/* wins) --------------------------

    if not site_root.exists():
        @app.get("/")
        def _no_build() -> dict:
            return {
                "error": f"No built site at {site_root}",
                "hint": "Run `docstrap build` first.",
            }
    else:
        app.mount("/", StaticFiles(directory=str(site_root), html=True), name="site")

    return app


def run(site_root: Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the app under uvicorn (blocks the caller)."""
    import uvicorn

    app = make_app(site_root)
    uvicorn.run(app, host=host, port=port, log_level="info")

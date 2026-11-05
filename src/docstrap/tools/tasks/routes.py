"""The task tool's server routes: the decisions recorded on one page.

``GET``   ``…/{project}/{doc_slug}/decisions``   every decision recorded
                                                  from this page, by task
                                                  id, and where the page's
                                                  "answers done" prompt
                                                  posts
``POST``  ``…/{project}/{doc_slug}/decisions``   record one decision on
                                                  one task

The path is the declaration's; nothing here writes one down. Both
operations are on the one collection and are told apart by method, never
by a sub-path (``declaration.check_route_separation``).

A decision is an answer in the project's answer store, keyed on this
page's document id and the task — :mod:`docstrap.tools.tasks.decisions`
says exactly how. The POST takes one task: there is no bulk write, so a
decision is always made on a row someone was looking at.

The "answers done" prompt is not this tool's. It is the qapanels
document-scope POST, which runs the configured
command with this page's project and path; the GET hands back its URL,
resolved here like every other route, or None when no command is
configured — which is what hides the prompt. Nothing is delivered beside
the page on a save: the answer addendum is what a document's
QUESTIONS decided, and a task decision is not one.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from docstrap import answers as answer_store
from docstrap import answers_done
from docstrap import metadata as meta
from docstrap import projectscope
from docstrap.tools import registry
from docstrap.tools.declaration import ToolDeclaration
from docstrap.tools.launcher import PageContext, resolve_alt_route
from docstrap.tools.tasks import decisions


class DecisionSubmission(BaseModel):
    """One decision on one task: an action from ``decisions.ACTIONS`` and a note."""

    task_id: str
    action: str
    note: str = ""


def _scope(project: str) -> projectscope.ProjectScope:
    try:
        return projectscope.resolve_slug(project)
    except projectscope.ScopeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _source(scope: projectscope.ProjectScope, doc_slug: str):
    found = scope.document_for_slug(doc_slug)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=f"{scope.slug} declares no document with the slug {doc_slug!r}",
        )
    return found


def _answers_done_route(project: str, doc_slug: str) -> Optional[str]:
    if answers_done.configured_command() is None:
        return None
    return resolve_alt_route(registry.get("qapanels"), PageContext(project, doc_slug))


def register(app, declaration: ToolDeclaration) -> tuple[str, ...]:
    """Mount the decisions collection. Returns the path mounted."""
    path = declaration.server_route_prefix
    assert path is not None, "tasks declares an api_collection"

    @app.get(path)
    def page_decisions(project: str, doc_slug: str) -> dict:
        scope = _scope(project)
        source = _source(scope, doc_slug)
        # Reading registers nothing: a page nobody has decided on yet has
        # no document id, and so no decisions.
        registered = meta.get_document_by_path(str(source.resolve()))
        found = decisions.on_page(scope.slug, registered.id) if registered else {}
        return {
            "decisions": {task_id: d.to_json() for task_id, d in found.items()},
            "actions": list(decisions.ACTIONS),
            "answersDoneRoute": _answers_done_route(scope.slug, doc_slug),
        }

    @app.post(path)
    def decide(project: str, doc_slug: str, payload: DecisionSubmission) -> dict:
        scope = _scope(project)
        source = _source(scope, doc_slug)
        doc_id = answer_store.document_id_for(source, scope.slug)
        try:
            stored = decisions.record(
                scope.slug,
                doc_id=doc_id,
                document=scope.display_path(source),
                task_id=payload.task_id,
                action=payload.action,
                note=payload.note,
            )
        except (decisions.DecisionError, answer_store.AnswerStoreError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {
            "taskId": stored.task_id,
            "key": answer_store.key_for(doc_id, decisions.label_for(stored.task_id)),
            "decision": stored.to_json(),
        }

    return (path,)

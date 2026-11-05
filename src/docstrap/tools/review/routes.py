"""The review tool's server routes.

Mounted by :mod:`docstrap.tools.mounting`, which hands this module the
declaration. The path comes from ``declaration.route_prefix``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import yaml
from fastapi import HTTPException
from pydantic import BaseModel

from docstrap import drafts
from docstrap.slugs import slugify
from docstrap.tools.declaration import ToolDeclaration


class ReviewSubmission(BaseModel):
    """Review tool POST body.

    Machine-collected sentence and section marks from the tool; the
    review file is written with these under YAML frontmatter and empty
    reactions to X-marked sentences appended in the body.
    """

    sentence_marks: list[dict[str, Any]]
    section_marks: list[dict[str, Any]]
    reviewer: Optional[str] = None
    summary: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def register(app, declaration: ToolDeclaration) -> tuple[str, ...]:
    """Mount the reviews endpoint. Returns the paths mounted."""
    path = declaration.server_route_prefix
    assert path is not None, "review declares an api_collection"

    @app.post(path)
    def submit_review(project: str, doc_slug: str, payload: ReviewSubmission) -> dict:
        try:
            root = drafts.require(project)
        except drafts.NoDraftRoot as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        # The identity stays the path it is — it is recorded verbatim as
        # `reviewed_doc` below. Only the FILENAME is flattened, through
        # the one slugifier, because a filename is one segment and a
        # document identity is not.
        doc_slug_safe = slugify(doc_slug)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = root / f"{doc_slug_safe}_review-{timestamp}.md"

        # YAML frontmatter with the machine-collected data.
        frontmatter = {
            "reviewer": payload.reviewer,
            "reviewed_doc": doc_slug,
            "submitted_at": _now_iso(),
            "summary": payload.summary,
            "sentence_marks": payload.sentence_marks,
            "section_marks": payload.section_marks,
        }
        # Reactions body: one empty slot per X-marked sentence.
        x_marked = [
            s for s in payload.sentence_marks if s.get("mark") in ("X", "x", "reject", -1)
        ]

        lines: list[str] = ["---\n"]
        lines.append(yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True))
        lines.append("---\n\n")
        lines.append(f"# Review — {doc_slug}\n\n")
        if payload.summary:
            lines.append(f"{payload.summary}\n\n")
        if x_marked:
            lines.append("## Reactions to rejected sentences\n\n")
            for s in x_marked:
                snippet = s.get("text") or s.get("id") or "(sentence)"
                lines.append(f"### {snippet}\n\n> _(reaction:)_ \n\n")
        target.write_text("".join(lines), encoding="utf-8")

        return {"written_to": str(target), "x_marked_count": len(x_marked)}

    return (path,)

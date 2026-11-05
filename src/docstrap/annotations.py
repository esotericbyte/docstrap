"""Annotations SQLite store — separate DB file from metadata.

Stores W3C Web Annotation JSON-LD documents. Separated from metadata.db
so annotations can be backed up, migrated, or replaced independently.

The app server exposes a minimum subset of the W3C Web Annotation
Protocol — enough for Annotorious to read and write.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from docstrap import paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS annotations (
  id           TEXT PRIMARY KEY,
  target_doc   TEXT NOT NULL,
  motivation   TEXT,
  body_json    TEXT NOT NULL,
  target_json  TEXT NOT NULL,
  creator      TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS annotations_target_doc ON annotations(target_doc);
"""


class AnnotationError(Exception):
    """Raised for invalid annotation data or missing IDs."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_annotation_id() -> str:
    """Generate a fresh annotation URI (opaque UUID)."""
    return f"urn:docstrap:annotation:{uuid.uuid4()}"


@contextmanager
def connect(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """Yield a WAL-mode SQLite connection to the annotations DB."""
    path = db_path or paths.annotations_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(db_path: Optional[Path] = None) -> Path:
    """Create the annotations database if it doesn't exist. Return its path."""
    path = db_path or paths.annotations_db_path()
    with connect(path):
        pass
    return path


@dataclass
class Annotation:
    id: str
    target_doc: str
    motivation: Optional[str]
    body: Any
    target: Any
    creator: Optional[str]
    created_at: str
    updated_at: str

    def to_w3c(self) -> dict[str, Any]:
        """Serialise as a W3C Web Annotation JSON-LD document."""
        doc: dict[str, Any] = {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": self.id,
            "type": "Annotation",
            "target": self.target,
            "body": self.body,
            "created": self.created_at,
            "modified": self.updated_at,
        }
        if self.motivation:
            doc["motivation"] = self.motivation
        if self.creator:
            doc["creator"] = self.creator
        return doc


def _row_to_annotation(row: sqlite3.Row) -> Annotation:
    return Annotation(
        id=row["id"],
        target_doc=row["target_doc"],
        motivation=row["motivation"],
        body=json.loads(row["body_json"]),
        target=json.loads(row["target_json"]),
        creator=row["creator"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _extract_target_doc(target: Any) -> str:
    """Pull the docstrap document URI out of a W3C target field.

    Accepts a string (the URI directly), a single dict with `source` or
    `id` key, or a list of such dicts. Returns the first matching URI.
    """
    if isinstance(target, str):
        return target
    if isinstance(target, dict):
        return target.get("source") or target.get("id") or ""
    if isinstance(target, list) and target:
        first = target[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("source") or first.get("id") or ""
    return ""


def list_for_target(target_doc: str, db_path: Optional[Path] = None) -> list[Annotation]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM annotations WHERE target_doc = ? ORDER BY created_at",
            (target_doc,),
        ).fetchall()
        return [_row_to_annotation(r) for r in rows]


def get(annotation_id: str, db_path: Optional[Path] = None) -> Optional[Annotation]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM annotations WHERE id = ?", (annotation_id,)
        ).fetchone()
        return _row_to_annotation(row) if row else None


def create(
    body: Any,
    target: Any,
    motivation: Optional[str] = None,
    creator: Optional[str] = None,
    annotation_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Annotation:
    """Create a new annotation. Returns the stored annotation."""
    target_doc = _extract_target_doc(target)
    if not target_doc:
        raise AnnotationError(
            "annotation target must resolve to a document URI (string, or dict with 'source'/'id')"
        )
    ann_id = annotation_id or _new_annotation_id()
    now = _now_iso()
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO annotations (id, target_doc, motivation, body_json, target_json, creator, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ann_id,
                target_doc,
                motivation,
                json.dumps(body),
                json.dumps(target),
                creator,
                now,
                now,
            ),
        )
    return Annotation(
        id=ann_id,
        target_doc=target_doc,
        motivation=motivation,
        body=body,
        target=target,
        creator=creator,
        created_at=now,
        updated_at=now,
    )


def update(
    annotation_id: str,
    body: Any = None,
    target: Any = None,
    motivation: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Annotation:
    """Patch an existing annotation. Only supplied fields are updated."""
    now = _now_iso()
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM annotations WHERE id = ?", (annotation_id,)
        ).fetchone()
        if not row:
            raise AnnotationError(f"no such annotation: {annotation_id}")
        new_body = body if body is not None else json.loads(row["body_json"])
        new_target = target if target is not None else json.loads(row["target_json"])
        new_motivation = motivation if motivation is not None else row["motivation"]
        new_target_doc = _extract_target_doc(new_target) or row["target_doc"]
        conn.execute(
            "UPDATE annotations SET body_json = ?, target_json = ?, motivation = ?, "
            "target_doc = ?, updated_at = ? WHERE id = ?",
            (
                json.dumps(new_body),
                json.dumps(new_target),
                new_motivation,
                new_target_doc,
                now,
                annotation_id,
            ),
        )
    result = get(annotation_id, db_path)
    assert result is not None
    return result


def delete(annotation_id: str, db_path: Optional[Path] = None) -> bool:
    """Delete an annotation by ID. Returns True if a row was removed."""
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
        return cur.rowcount > 0

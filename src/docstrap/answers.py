"""The keyed answer store — one file per project, and one owner for it.

An answer to a question a document poses lives in ``<draft-root>/answers.md``: a markdown
file whose YAML front-matter carries the index and whose body carries the
prose. Its writers are the qa tool, the qapanels instrument and the task
tool, which records a decision on a task as an answer
(``tools/tasks/decisions.py``), and this module is the only thing that reads or writes the format — the same
single-owner rule ``docstrap.slugs`` has for names and ``docstrap.drafts``
has for where a project's derivatives go, and for the same reason. A second implementation
of either of those is what orphaned submitted answers once.

**The key** is the metadata store's document id and the
question's own label inside that document, joined by a colon::

    01J9F4V4T4XW9A0RCM6QK2S8YZ:Q4

The document id survives a rename and a slug does not, which matters:
a document moved from one folder to another — a proposal promoted, say —
would orphan every answer keyed on its slug. The label is the author's own — the `Q<n>` that
:mod:`docstrap.questions` reads, or the `:question-id:` a
``docstrap-questions`` directive declares — and the id half is what keeps
two documents' `Q1`s apart.

**Writing a key twice supersedes.** The row is replaced and the body
section rewritten in place. Nothing appends, which is the defect this
replaced: the earlier per-document answer file treated a question id as
decorative italic text, so posting the same question twice stacked two
sections under the same heading.

**An answer counts when a person says it is finished.** Every
write states whether it is a draft or a submission, and :func:`put`
requires the caller to say which — the first real run counted an answer
at three characters because an autosave was indistinguishable from a
reply, and a default here would put that guess back. A consumer acting
on decisions reads :func:`submitted`, never :func:`read`.

**A row written before that distinction existed counts as submitted.**
``Answer.submitted`` is tri-state: ``True``, ``False``, and ``None`` for
a row whose front-matter carries no ``submitted`` field at all. ``None``
reads as submitted through :attr:`Answer.is_submitted`, because under the
rule those rows were written under, storing an answer *was* finishing it;
reading them as drafts would retroactively un-answer ten real
decisions already in a store. ``None`` is also never written back, so an
untouched legacy row keeps its bytes.

**This is not an index of questions.** Questions live in the documents and
are found by scanning them (:mod:`docstrap.questions`);
nothing here records what questions exist, and the question's *text* is
deliberately not stored. A key whose question has since been deleted is a
stale answer, not a question this store believes in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import yaml

from docstrap import drafts
from docstrap.frontmatter import split_front_matter

#: The one filename. One file per project, not one per document: the key
#: is document-id-anchored, and a per-document filename would be
#: slug-anchored and would reintroduce the orphaning the key removes.
ANSWERS_FILENAME = "answers.md"

#: The superseded answers, beside the current ones. A separate
#: file rather than extra rows in ``answers.md``: every consumer of that
#: file reads its rows as the project's current answers, and history rows
#: mixed in among them would change what that file means. Here they are
#: their own thing and nothing that reads answers.md changes at all.
HISTORY_FILENAME = "answers-history.md"

#: Front-matter key holding the index rows. The same key in both files.
INDEX_KEY = "answers"

#: A body section opens with `## <key>`; anything after the key on that
#: line is human-facing decoration and is not read back. The key's shape
#: is required here — two colon-separated runs with no whitespace — so an
#: ordinary `## Heading` written inside an answer stays part of that
#: answer rather than starting a section nothing indexed.
#:
#: Two suffixed forms sit in the same space and need no change here,
#: because a suffix is part of the second run: `<key>#draft` holds a
#: revision someone is still typing, and `<key>#r<n>` holds the n-th
#: superseded answer in the history file.
_SECTION_RE = re.compile(r"^##[ \t]+(?P<key>[^\s:]+:[^\s:]+)[ \t]*(?:—.*)?$")

#: The section suffix for an unsubmitted revision.
DRAFT_SUFFIX = "#draft"

#: What stands in the body when a section has no prose, so the file still
#: reads. It is the renderer's own mark and never something a person
#: typed, so it is mapped back to the empty string on the way in.
EMPTY_PROSE = "*(no answer text)*"


class AnswerStoreError(Exception):
    """The answer file on disk could not be read as an answer file."""


@dataclass(frozen=True)
class Answer:
    """One answer, as the store holds it."""

    key: str
    #: The metadata store's document id — the first half of the key.
    doc_id: str
    #: The question's own label inside that document — the second half.
    label: str
    #: Where the document was when the answer was given. Reported, never
    #: keyed on: it is here so a reader can find the question again.
    document: str
    #: The SUBMITTED answer prose, as markdown. Empty when nobody has
    #: submitted an answer to this question yet — a draft does not live
    #: here, because a draft overwriting this is what would make a
    #: decision vanish from every consumer while its author retyped it.
    text: str
    #: When the answer was given, ISO-8601 UTC to the second.
    answered_at: str
    #: Who gave it, when anyone said. Optional and usually absent.
    answered_by: Optional[str] = None
    #: Whether a person said this answer was finished. Tri-state:
    #: ``True`` submitted, ``False`` a draft still being typed, ``None``
    #: a row written before the distinction existed. See
    #: :attr:`is_submitted` for what ``None`` means to a consumer.
    submitted: Optional[bool] = None
    #: When it was submitted, ISO-8601 UTC to the second. Set only on a
    #: submission; a draft leaves it absent, and so does a legacy row.
    submitted_at: Optional[str] = None
    #: An answer someone is still typing — either a first answer nobody
    #: has finished, or a revision of the submitted one above. `None`
    #: when there is nothing unsubmitted against this question.
    draft: Optional[str] = None
    #: When the draft was last saved.
    drafted_at: Optional[str] = None
    #: Set only on a row in the HISTORY file: which superseded answer
    #: this is, counting from 1. `None` on a current answer.
    revision: Optional[int] = None
    #: Set only on a row in the HISTORY file: when this answer stopped
    #: being the current one.
    superseded_at: Optional[str] = None

    @property
    def section_key(self) -> str:
        """The body heading this answer's prose lives under."""
        return self.key if self.revision is None else f"{self.key}#r{self.revision}"

    @property
    def draft_section_key(self) -> str:
        """The body heading this answer's unsubmitted revision lives under."""
        return f"{self.key}{DRAFT_SUFFIX}"

    @property
    def has_draft(self) -> bool:
        return bool(self.draft and self.draft.strip())

    @property
    def editable_text(self) -> str:
        """What to put back in front of whoever is answering.

        Their own unfinished revision if they have one, and the submitted
        answer otherwise — so returning to a question resumes where they
        stopped rather than where the record stopped.
        """
        return self.draft if self.has_draft else self.text

    @property
    def is_submitted(self) -> bool:
        """Whether a consumer may act on this answer.

        ``None`` counts. A row carrying no ``submitted`` field was
        written under the rule that storing an answer finished it, and
        that is how those answers travelled and closed work.
        """
        return True if self.submitted is None else self.submitted

    def row(self) -> dict[str, object]:
        """The front-matter row for this answer, in written order."""
        row: dict[str, object] = {
            "key": self.key,
            "document": self.document,
            "label": self.label,
            "answered_at": self.answered_at,
        }
        if self.submitted is not None:
            row["submitted"] = self.submitted
        if self.submitted_at:
            row["submitted_at"] = self.submitted_at
        if self.has_draft:
            row["drafted_at"] = self.drafted_at or ""
        if self.revision is not None:
            row["revision"] = self.revision
        if self.superseded_at:
            row["superseded_at"] = self.superseded_at
        if self.answered_by:
            row["answered_by"] = self.answered_by
        return row


def key_for(doc_id: str, label: str) -> str:
    """The key an answer hangs on: document id, colon, question label."""
    doc_id = doc_id.strip()
    label = label.strip()
    if not doc_id:
        raise AnswerStoreError("an answer key needs a document id")
    if not label:
        raise AnswerStoreError("an answer key needs a question label")
    if ":" in label:
        raise AnswerStoreError(
            f"question label {label!r} contains ':', which separates the key's "
            f"two halves"
        )
    return f"{doc_id}:{label}"


def store_path(project_slug: str) -> Path:
    """The project's answer file, in its draft root (:mod:`docstrap.drafts`).

    A project with no draft root has nowhere to keep one, which is an
    :class:`AnswerStoreError` rather than a directory invented for it.
    """
    return _draft_root(project_slug) / ANSWERS_FILENAME


def history_path(project_slug: str) -> Path:
    """The project's superseded answers, beside its answer file."""
    return _draft_root(project_slug) / HISTORY_FILENAME


def _draft_root(project_slug: str) -> Path:
    try:
        return drafts.require(project_slug)
    except drafts.NoDraftRoot as exc:
        raise AnswerStoreError(str(exc)) from exc


def _existing(project_slug: str, filename: str) -> Path | None:
    """``filename`` in the project's draft root, or None — no root is no file."""
    root = drafts.draft_root(project_slug)
    if root is None:
        return None
    path = root / filename
    return path if path.is_file() else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --- reading ---------------------------------------------------------------


def read(project_slug: str) -> list[Answer]:
    """Every answer the project holds, in the order the file lists them.

    A missing file is an empty store, not an error — a project nobody has
    answered anything in has no answer file. A file whose front-matter
    cannot be parsed raises: silently returning nothing there would look
    identical to the empty case and would then be overwritten.
    """
    path = _existing(project_slug, ANSWERS_FILENAME)
    if path is None:
        return []
    return parse(path.read_text(encoding="utf-8"), source=path)


def get(project_slug: str, key: str) -> Optional[Answer]:
    """One answer by key, or None."""
    for answer in read(project_slug):
        if answer.key == key:
            return answer
    return None


def submitted(project_slug: str) -> list[Answer]:
    """Every answer a person finished — what a consumer may act on.

    This is the read that everything downstream of the answer loop uses.
    :func:`read` returns drafts too, because the editor needs its own
    unfinished text back; a consumer that called it would be doing again
    what counted a reply at three characters.
    """
    return [answer for answer in read(project_slug) if answer.is_submitted]


def history(project_slug: str, key: Optional[str] = None) -> list[Answer]:
    """Every answer this project has superseded, oldest first.

    A later answer replaces an earlier one rather than being rejected,
    and this is the half of that which makes the replaced one
    recoverable rather than lost. Pass ``key`` for one question's
    history; the entries carry ``revision``, counting from 1.
    """
    path = _existing(project_slug, HISTORY_FILENAME)
    if path is None:
        return []
    held = parse(path.read_text(encoding="utf-8"), source=path)
    if key is not None:
        held = [answer for answer in held if answer.key == key]
    return sorted(held, key=lambda answer: answer.revision or 0)


def parse(text: str, *, source: Path | None = None) -> list[Answer]:
    """Parse answer-file text. The index decides; the body supplies prose."""
    where = f" in {source}" if source is not None else ""
    block = split_front_matter(text)
    if block.malformed:
        raise AnswerStoreError(f"unreadable answer file{where}: {block.error}")

    rows = block.data.get(INDEX_KEY) or []
    if not isinstance(rows, list):
        raise AnswerStoreError(
            f"unreadable answer file{where}: `{INDEX_KEY}` is not a list"
        )

    bodies = _body_sections(block.body)
    answers: list[Answer] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("key"):
            raise AnswerStoreError(
                f"unreadable answer file{where}: an `{INDEX_KEY}` row has no key"
            )
        key = str(row["key"])
        doc_id, _, label = key.partition(":")
        # Absent and present-but-false are different states, so this asks
        # whether the field is there before it asks what it says.
        flag = row.get("submitted", None)
        revision = row.get("revision")
        section = key if revision is None else f"{key}#r{int(revision)}"
        draft = bodies.get(f"{key}{DRAFT_SUFFIX}") or None
        answers.append(
            Answer(
                key=key,
                doc_id=doc_id,
                label=label or str(row.get("label") or ""),
                document=str(row.get("document") or ""),
                text=bodies.get(section, ""),
                answered_at=str(row.get("answered_at") or ""),
                answered_by=(str(row["answered_by"]) if row.get("answered_by") else None),
                submitted=None if flag is None else bool(flag),
                submitted_at=(
                    str(row["submitted_at"]) if row.get("submitted_at") else None
                ),
                draft=draft,
                drafted_at=(
                    str(row["drafted_at"]) if row.get("drafted_at") else None
                ),
                revision=None if revision is None else int(revision),
                superseded_at=(
                    str(row["superseded_at"]) if row.get("superseded_at") else None
                ),
            )
        )
    return answers


def _body_sections(body: str) -> dict[str, str]:
    """Map each `## <key>` heading to the prose under it."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in body.splitlines():
        match = _SECTION_RE.match(line)
        if match:
            current = sections.setdefault(match.group("key"), [])
            continue
        if current is not None:
            current.append(line)
    prose = {key: "\n".join(lines).strip() for key, lines in sections.items()}
    return {
        key: ("" if text == EMPTY_PROSE else text) for key, text in prose.items()
    }


# --- writing ---------------------------------------------------------------


def put(
    project_slug: str,
    *,
    doc_id: str,
    label: str,
    document: str,
    text: str,
    submitted: bool,
    answered_by: Optional[str] = None,
    answered_at: Optional[str] = None,
    submitted_at: Optional[str] = None,
) -> Answer:
    """Record one answer, superseding any earlier answer to the same key.

    ``submitted`` has no default and is required of every caller. A
    default would be a guess about whether a person has finished, and a
    guess is what read a reply at three characters; the one question this
    store exists to answer cleanly is when an answer counts.

    The two branches are different writes.

    **A draft never disturbs the submitted answer.** It lands in its own
    field beside the decision rather than on top of it, because a person
    retyping their reply must not make the existing decision disappear
    from every consumer while they do it.

    **A submission supersedes, and keeps what it superseded.** A later
    answer replaces an earlier one rather than being rejected — the
    person rewriting their own reply is ordinary — and the replaced answer
    is appended to the history file first, so the earlier one is
    recoverable rather than lost.

    Returns the answer as stored. The file is rewritten whole, which is
    what makes superseding possible at all — but the rendering is
    deterministic and keeps existing rows in place, so a re-answer is one
    changed row plus one changed body section in the diff.
    """
    key = key_for(doc_id, label)
    stamp = answered_at or _now_iso()
    value = text.strip()

    existing = read(project_slug)
    held = next((answer for answer in existing if answer.key == key), None)

    if submitted:
        # What is being replaced, if it was a decision and it differs, is
        # kept before it stops being the current answer.
        if held is not None and held.is_submitted and held.text.strip() != value:
            _append_history(project_slug, held, superseded_at=stamp)
        answer = Answer(
            key=key,
            doc_id=doc_id.strip(),
            label=label.strip(),
            document=document,
            text=value,
            answered_at=stamp,
            answered_by=answered_by or None,
            submitted=True,
            submitted_at=submitted_at or stamp,
            # Submitting is what the draft was heading towards, so it is
            # spent. Leaving it would show a revision still in flight.
            draft=None,
            drafted_at=None,
        )
    else:
        current = held.text if held is not None else ""
        answer = Answer(
            key=key,
            doc_id=doc_id.strip(),
            label=label.strip(),
            document=document,
            text=current,
            # A draft does not move the submitted answer's timestamp.
            answered_at=(
                held.answered_at if (held is not None and held.is_submitted) else stamp
            ),
            answered_by=(
                answered_by
                or (held.answered_by if held is not None else None)
                or None
            ),
            submitted=(held.submitted if held is not None else False),
            submitted_at=(held.submitted_at if held is not None else None),
            # A draft that says what the submitted answer already says is
            # not a revision in flight, and neither is an emptied one.
            draft=(value or None) if value != current.strip() else None,
            drafted_at=stamp if (value and value != current.strip()) else None,
        )

    merged = [answer if other.key == key else other for other in existing]
    if held is None:
        merged.append(answer)

    path = store_path(project_slug)
    path.write_text(render(project_slug, merged), encoding="utf-8")
    return answer


def _append_history(
    project_slug: str, superseded: Answer, *, superseded_at: str
) -> Answer:
    """Keep one replaced answer, numbered, in the history file."""
    kept = history(project_slug)
    revision = sum(1 for entry in kept if entry.key == superseded.key) + 1
    entry = Answer(
        key=superseded.key,
        doc_id=superseded.doc_id,
        label=superseded.label,
        document=superseded.document,
        text=superseded.text,
        # The timestamps the superseded answer carried, plus when it
        # stopped being current. Nothing about it is rewritten.
        answered_at=superseded.answered_at,
        answered_by=superseded.answered_by,
        submitted=True,
        submitted_at=superseded.submitted_at,
        revision=revision,
        superseded_at=superseded_at,
    )
    path = history_path(project_slug)
    path.write_text(render(project_slug, kept + [entry], kind="history"), encoding="utf-8")
    return entry


_BLURB = {
    "answers": (
        "Written by docstrap. One section per "
        "key, and a\nkey is a document id and the question's own label. The "
        "questions themselves live in the\ndocuments and are found by scanning "
        "them — nothing here records what questions exist."
    ),
    "history": (
        "Written by docstrap. Answers that were "
        "superseded by a\nlater one, so the earlier decision is recoverable "
        "rather than lost. The CURRENT answers\nare in `answers.md`; nothing "
        "here is current, and a key may appear more than once."
    ),
}


#: The heading each of the two files opens with, before the project slug.
_TITLES = {"answers": "Answers", "history": "Superseded answers"}


def render(
    project_slug: str, answers: Iterable[Answer], *, kind: str = "answers"
) -> str:
    """One answer file's text, given the answers it should hold.

    Front-matter carries the index, one flow-style row per answer so a
    change to an answer's metadata is one changed line. The prose lives in
    the body as markdown and is never embedded in the YAML: a block scalar
    would rewrite the whole block on any change and is unreadable to hand
    edit, which is why that shape was rejected.

    ``kind`` picks which of the two files this is — the current answers
    or the superseded ones. The format is the same either way, and one
    renderer writes both so the two cannot drift apart.
    """
    held = list(answers)
    lines = [
        "---",
        f"{INDEX_KEY}:",
    ]
    for answer in held:
        lines.append(f"  - {_flow_row(answer.row())}")
    if not held:
        lines[-1] = f"{INDEX_KEY}: []"
    lines.append("---")
    lines.append("")
    lines.append(f"# {_TITLES.get(kind, _TITLES['answers'])} — {project_slug}")
    lines.append("")
    lines.append(_BLURB.get(kind, _BLURB["answers"]))
    lines.append("")
    for answer in held:
        # A question with nothing but a draft against it has no answer to
        # show, so it gets no answer section — only the draft one below.
        if answer.text or not answer.has_draft:
            lines.extend(_section(answer.section_key, answer.document, answer.text))
        # An unsubmitted revision sits under the answer it would replace,
        # in its own section, so nothing reading the key's own section
        # can pick it up by accident.
        if answer.has_draft:
            lines.extend(
                _section(
                    answer.draft_section_key,
                    answer.document,
                    answer.draft or "",
                    note="not submitted",
                )
            )
    return "\n".join(lines).rstrip("\n") + "\n"


#: What the published page says when the answer file cannot be read. It
#: fails closed: an unreadable file may hold drafts, and nothing can tell.
UNREADABLE_PUBLICATION = (
    "# Answers\n\n"
    "This answer file could not be read, so nothing in it is published.\n"
)


def publishable(text: str) -> str:
    """An answer file's text as the built site may show it: no draft, ever.

    The rule is the answers API's (no draft is ever served), applied to the other place an
    answer file is published — the site, which renders the draft source's
    ``answers.md`` as a page. A question answered only by a draft
    loses its row and its section, so not even the fact that a draft
    exists is shown; a submitted answer keeps its prose and loses the
    revision being typed over it.

    Rendered by :func:`render`, so the page has the stored file's shape.
    This is a view for the build, held in memory: nothing writes it back,
    and the stored file is untouched.
    """
    try:
        held = parse(text)
    except AnswerStoreError:
        return UNREADABLE_PUBLICATION
    kind, project = _heading(split_front_matter(text).body)
    shown = [
        replace(answer, draft=None, drafted_at=None)
        for answer in held
        if answer.is_submitted
    ]
    return render(project, shown, kind=kind)


def _heading(body: str) -> tuple[str, str]:
    """Which file this is and whose, read back off the heading `render` wrote."""
    for line in body.splitlines():
        if not line.strip():
            continue
        for kind, title in _TITLES.items():
            if line.startswith(f"# {title} — "):
                return kind, line.removeprefix(f"# {title} — ").strip()
        break
    return "answers", ""


def _section(
    key: str, document: str, text: str, *, note: str | None = None
) -> list[str]:
    """One `## <key>` heading and the prose under it.

    Everything after the key is decoration `_SECTION_RE` skips, but it
    only skips it after an em dash — so a note with no document to hang
    off still gets one.
    """
    decoration = " ".join(part for part in (document, f"({note})" if note else "") if part)
    heading = f"## {key}" + (f" — {decoration}" if decoration else "")
    return [heading, "", text or EMPTY_PROSE, ""]


def _flow_row(row: dict[str, object]) -> str:
    """One index row as a single flow-style YAML line."""
    dumped = yaml.safe_dump(
        row, default_flow_style=True, sort_keys=False, width=10**6, allow_unicode=True
    )
    return dumped.strip()


# --- the document half of the key ------------------------------------------


def document_id_for(path: Path, project_slug: str) -> str:
    """The metadata store's id for ``path``, registering it if it is new.

    Resolve-or-create, the same thing ``docstrap status <path>`` does
    before it can report or set a status. An answer needs an anchor that
    survives a rename, and the metadata store is where document identity
    lives; a document nobody has touched with docstrap yet simply has
    not been given one, and answering a question in it is a reason to.
    """
    from docstrap import metadata as meta

    absolute = str(Path(path).expanduser().resolve())
    return meta.get_or_create_document(project_slug, absolute).id

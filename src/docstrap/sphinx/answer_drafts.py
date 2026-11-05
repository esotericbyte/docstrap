"""Sphinx extension: the published answer page carries no draft.

A markdown-layout build mirrors a project's ``draft`` source under that
source's mount, and the answer store's ``answers.md`` is among it, so
Sphinx renders the store as a page. The store holds drafts as well as
decisions, and a draft is never
published — not its text, and not the fact that one exists. The answers
API keeps that rule by reading :func:`docstrap.answers.submitted`; this
keeps it on the site, the second place an answer file is published.

Which mount the store is read under is the build's to say: it passes the
mount of the project's draft source as :data:`DRAFT_MOUNT_CONFIG`, and a
build with no draft source passes None and this does nothing.

It works on the source as Sphinx reads it, through ``source-read``,
because the mirror links the file rather than copying it: the page is
replaced in memory with :func:`docstrap.answers.publishable`, and nothing
is written, here or in the store. A build writes no markdown, and this does not change that.
"""
from __future__ import annotations

from docstrap import answers

#: The conf.py value naming the mount of the project's draft source:
#: ``''`` for the project root, None when the build has no draft source.
DRAFT_MOUNT_CONFIG = "docstrap_draft_mount"

_ANSWERS_STEM = answers.ANSWERS_FILENAME.removesuffix(".md")


def answers_docname(draft_mount: str | None) -> str | None:
    """The docname the answer store is read under, for a draft source's mount."""
    if draft_mount is None:
        return None
    return f"{draft_mount}/{_ANSWERS_STEM}" if draft_mount else _ANSWERS_STEM


def _on_source_read(app, docname: str, source: list[str]) -> None:
    if docname == answers_docname(getattr(app.config, DRAFT_MOUNT_CONFIG, None)):
        source[0] = answers.publishable(source[0])


def setup(app):
    """Sphinx entry point."""
    app.add_config_value(DRAFT_MOUNT_CONFIG, None, "env")
    app.connect("source-read", _on_source_read)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

"""Round-trip safety for the front-matter splitter.

A tool that touches front-matter must round-trip
foreign keys unchanged, including key order and comments where the parser
allows. These tests hold the splitter to the stronger version of that
promise — the whole document comes back byte for byte, not just the keys.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap.frontmatter import read_front_matter, split_front_matter
from docstrap.strapdance import NAMESPACE


def test_document_with_foreign_namespace_and_bare_keys_round_trips(collection: Path):
    """The requirement, stated directly: read it, put it back, no diff."""
    document = collection / "docs" / "proposals" / "coexisting-namespaces.md"
    original = document.read_bytes()

    block = read_front_matter(document)

    assert block.to_text().encode("utf-8") == original
    # And the document on disk is untouched — the reader never writes.
    assert document.read_bytes() == original


def test_round_trip_preserves_comments_and_key_order(collection: Path):
    document = collection / "docs" / "proposals" / "coexisting-namespaces.md"
    block = read_front_matter(document)

    assert "# A hand-written block." in block.raw
    assert "whatever:   it wants" in block.raw, "odd spacing survives verbatim"
    assert list(block.data) == ["title", "some_other_tool", NAMESPACE, "zz_last_key"]
    assert block.keys_other_than(NAMESPACE) == ("title", "some_other_tool", "zz_last_key")


def test_every_fixture_document_round_trips(collection: Path, workspace: Path):
    """Sweep both fixture trees; malformed and front-matter-less included."""
    documents = sorted(collection.rglob("*.md")) + sorted(workspace.rglob("*.md"))
    assert len(documents) >= 17

    for document in documents:
        original = document.read_bytes()
        assert read_front_matter(document).to_text().encode("utf-8") == original, document


def test_crlf_and_byte_order_mark_survive(tmp_path: Path):
    document = tmp_path / "windows.md"
    original = (
        "﻿---\r\n"
        "strapdance:\r\n"
        "  kind: note\r\n"
        "other_tool: {a: 1}\r\n"
        "---\r\n"
        "\r\n"
        "# A document written on Windows\r\n"
    ).encode("utf-8")
    document.write_bytes(original)

    block = read_front_matter(document)

    assert block.present
    assert block.data[NAMESPACE] == {"kind": "note"}
    assert block.to_text().encode("utf-8") == original


@pytest.mark.parametrize(
    "text",
    [
        "",
        "# No front matter at all\n",
        "---\n---\n",
        "---\n---\nbody with no trailing newline",
        "---\nkind: note\n...\nclosed with a YAML document-end marker\n",
        "not a delimiter\n---\nthis --- is not front matter\n",
        "---",
    ],
)
def test_split_is_lossless_for_awkward_shapes(text: str):
    assert split_front_matter(text).to_text() == text


def test_absent_front_matter_is_not_an_error():
    block = split_front_matter("# Just a document\n")

    assert not block.present
    assert not block.malformed
    assert block.data == {}
    assert block.body == "# Just a document\n"


def test_invalid_yaml_is_reported_not_repaired(collection: Path):
    document = collection / "docs" / "proposals" / "malformed.md"
    original = document.read_bytes()

    block = read_front_matter(document)

    assert block.present
    assert block.malformed
    assert "not valid YAML" in block.error
    assert block.data == {}
    assert block.to_text().encode("utf-8") == original
    assert document.read_bytes() == original


def test_unterminated_block_is_reported_not_repaired(collection: Path):
    document = collection / "docs" / "proposals" / "unterminated.md"
    original = document.read_bytes()

    block = read_front_matter(document)

    assert block.malformed
    assert "never closed" in block.error
    assert block.to_text().encode("utf-8") == original


def test_non_mapping_front_matter_is_reported():
    block = split_front_matter("---\n- one\n- two\n---\n\n# A list, not a mapping\n")

    assert block.malformed
    assert "must be a YAML mapping" in block.error
    assert block.data == {}
    assert block.body == "\n# A list, not a mapping\n"

"""The panels' one Finish: below the question list, never under an answer.

Autosave writes a draft that nothing downstream can see, and Finish is
the only thing that submits. Finish sat under
each answer, over the bottom of its field, and had to be pressed once per
question; on 2026-11-04 thirteen answers stayed drafts because none of
those buttons was. Now there is one, at the foot of the question list,
and it submits every draft in scope.

1. Its rules — which drafts, what label, when disabled, what is reported
   — are `ui/finish.ts`, proved under Node by `tests/qapanels/finish.test.ts`.
2. The editor has no submit control of its own, and the one Finish is
   rendered after the questions, in the list's own flow.
3. The committed bundle is the one built from this source.

That the drafts it submits go in through the existing route, and come out
submitted, is `test_answers.py`'s
``test_the_one_finish_submits_every_draft_on_the_page``.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from docstrap.tools import registry

PACKAGE = Path(__file__).resolve().parents[1]
QAPANELS = PACKAGE / "src" / "docstrap" / "tools" / "qapanels"
UI = QAPANELS / "ui"


def _node() -> str | None:
    node = shutil.which("node")
    if node is None:
        return None
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    match = re.match(r"v(\d+)\.(\d+)", version)
    # Type stripping arrived in 22.6.
    if not match or (int(match.group(1)), int(match.group(2))) < (22, 6):
        return None
    return node


def test_the_finish_rules_pass_under_node():
    node = _node()
    if node is None:
        pytest.skip("needs Node 22.6 or later, for --experimental-strip-types")
    result = subprocess.run(
        [node, "--experimental-strip-types", "--test", "tests/qapanels/finish.test.ts"],
        cwd=PACKAGE,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_answer_editor_has_no_submit_control():
    """Every save the editor makes is a draft; it has no button at all."""
    source = (UI / "AnswerEditor.svelte").read_text(encoding="utf-8")
    markup = source.split("</script>", 1)[1]
    assert "<button" not in markup
    assert "submitted: boolean" not in source, "the editor's save takes no submit flag"


def test_the_one_finish_is_below_the_last_question():
    """Passed as the list's footer, and rendered after the questions."""
    panels = (UI / "Panels.svelte").read_text(encoding="utf-8")
    footer = panels.index("{#snippet footer()}")
    assert panels.index("<QuestionList") < footer < panels.index("</QuestionList>")
    assert panels.count('class="finish"') == 1

    listing = (UI / "QuestionList.svelte").read_text(encoding="utf-8")
    assert listing.index("{#each documents") < listing.index("{@render footer?.()}")


def test_the_committed_bundle_carries_the_one_finish():
    bundle = (QAPANELS / "static" / registry.get("qapanels").js_bundle).read_text(
        encoding="utf-8"
    )
    assert "Submit revisions" in bundle and "Nothing to submit" in bundle, (
        "the committed build is stale: run `npm run build` in packages/docstrap"
    )
    assert "Submit this answer." not in bundle, "the per-answer Finish is still built in"

# docstrap doctor — what it reports, and what it will not do

`docstrap doctor` answers one question about a workspace: which documents
does no project actually own? It reports them, it can write a proposal
script, and it changes nothing else. Ever.

```
docstrap doctor --root .
docstrap doctor --root . --fix-plan /tmp/docstrap-fix.sh
docstrap doctor --root . --interactive --fix-plan /tmp/docstrap-fix.sh
```

## 1 The finding

A document is **ambiguously scoped** when the strapdance chain's answer to
"which project owns this?" came from the workspace root — or from nothing
at all.

The chain has four possible answerers for `project`, and three of them are
the same chain *step* (`position`), which is why the report names the
answerer as well as the step:

1. `explicit` — the document's own `strapdance.project` field. A real
   answer, and the only thing that can scope a root-level document.
2. `docstrap_project` — the nearest `.docstrap` project entry containing
   it. A real answer.
3. `workspace_member` — the uv workspace member whose directory contains
   it. A real answer.
4. `workspace_root` — the workspace root, because nothing else could say.
   **A finding.**
5. `none` — no `.docstrap` entry and no uv workspace above it at all.
   **A finding.**

Specification §3B.2 is why (4) is honest rather than wrong: a prompt or a
spec at the root of a repo often belongs to one member, and its position
cannot express that, because its position *is* the root. Doctor is the
command that says so out loud.

Doctor examines the workspace root's docs directory — `docs/` unless a
`.docstrap` names a different `docs_root`, or `--docs-dir` overrides both.
Excluded directories (`archive/`, `deprecated/`, and anything the
`.docstrap` lists in `exclude_dirs`) are skipped, as everywhere else.

## 2 The environment check

Doctor also reports firstmate operational homes below the examined root
that have not been declared `ignore: true` — the same detection
`docstrap firstmate-ignore-check` uses, folded in rather than
reimplemented. Doctor reports it; that command is the one that writes.
Use `--firstmate-root` to look somewhere other than `--root`.

## 3 It does not act

Roadmap §4A.7: nothing is altered in place. Doctor moves no file, edits no
document, and writes no `.docstrap`.

`--fix-plan <path>` writes one new file — a shell script nobody has run —
and refuses to overwrite anything already at that path. Every proposed
`git mv` in it is commented out unless a person named a destination, so a
plan run without further thought does nothing. Each entry also carries the
alternative that involves no move at all: declare the owner in the
document's front-matter.

`--interactive` asks, per finding, which directory should own it. The
answers shape the emitted script and nothing else; the files stay where
they are either way.

The exit code is 0 even when there are findings. A report of what is, is
not a failure.

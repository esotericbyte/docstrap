---
name: docstrap-lifecycle
description: Change a document's docstrap lifecycle status — and only ever when the user explicitly asked for that change and explicitly approved the specific document and the specific from-status → to-status transition. Uses the docstrap CLI; never touches the metadata database directly. Refuses to change status unprompted.
trigger:
  - User explicitly asks to promote, demote, or otherwise change a document's docstrap status
  - User asks what status a document currently has
---

# docstrap lifecycle status

This skill is deliberately the narrowest in the docstrap package. It exists to make one operation possible and to make every neighbouring operation impossible.

## The one thing this skill does

Change one document's lifecycle status, through the docstrap CLI, after the user asked for it and approved it.

## The two gates

Both must be open. Neither is inferable, and neither can be satisfied by something the user said about something else.

1. **Explicitly prompted.** The user asked for a status change. "Promote the WSL proposal to a spec" is a prompt. "This is basically a spec now", "we should probably call that a spec", and "the proposal is finished" are not — they are observations about a document, and acting on one is changing a person's records because they described a situation.
2. **Explicitly approved.** Before running the command, state the exact change and get a yes:

   > `docs/proposals/wsl-cross.md`: `proposal` → `spec`. Confirm?

   The approval must name the document and both ends of the transition. An approval of one change is not an approval of the next one, and it does not extend to other documents in the same directory or the same conversation.

## Never

1. **Never change a status unprompted.** Not while doing something else in the file, not as part of a larger task, not because the document plainly moved on. Notice it and say so; do not act.
2. **Never change status in bulk.** One document, one approval. A directory-wide sweep cannot satisfy gate 2, because a single yes cannot name every transition.
3. **Never write to the databases.** `metadata.db` and `annotations.db` are docstrap's, and the CLI is the only supported way in. No `sqlite3`, no Python one-liner, no direct file edit.
4. **Never edit the document to change its status.** A `status:` field in the document's front-matter is the author's declaration, and docstrap does not read it. Recording a lifecycle status is a separate act through the CLI. If the user wants the front-matter changed, that is an ordinary editing request and they must say so.
5. **Never invent a status.** The vocabulary is fixed below; an unrecognised value is rejected by the CLI, and guessing at a near-miss is worse than asking.

## The commands

Read the current status — always safe, no approval needed:

```
docstrap status <path>
```

It prints the document's path, project, current status, tags, and docstrap ID.

Change the status — only with both gates open:

```
docstrap status <path> <new-status>
```

It prints `<path>: status → <new-status>` on success.

Tags are a separate operation with the same two gates:

```
docstrap tag <path>              # report
docstrap tag <path> <tag>...     # replace the tag set — this REPLACES, it does not add
```

Because `docstrap tag` replaces rather than appends, quote the resulting full tag set back to the user before running it.

## The status vocabulary

`draft`, `proposal`, `spec`, `plan`, `active`, `archived`.

That is the whole list. It is enforced by docstrap, not by this skill, so a rejected value is a real error rather than a rule to work around.

## The usual sequence

1. The user asks for a status change.
2. Run `docstrap status <path>` to read the current value. Do this before proposing anything — the from-status must be observed, not assumed.
3. State the change as `<path>: <from> → <to>` and ask for confirmation.
4. On an explicit yes, run `docstrap status <path> <to>`.
5. Report what the CLI printed. If it failed, report the failure verbatim; do not retry with a different status.

If step 2 shows the document is already at the requested status, say so and stop. There is nothing to approve.

## Where the status shows up

The status lives in docstrap's metadata database and is rendered by the status tool as an inline badge on the built page. Changing it does not modify the document, and it does not rebuild the site — run `docstrap build` for that, as a separate request.

## Adjacent things that are not this skill

- **Which project owns a document**, and documents that no project clearly owns: `docstrap doctor`. It reports and proposes; it moves nothing.
- **Authoring or editing document content**: the `docstrap-authoring` skill.
- **Moving or renaming a document**: an ordinary file operation, and its own request. Doing it as part of a status change is exactly the scope creep the two gates exist to prevent.

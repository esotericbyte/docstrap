# To-do — promdance interning, the store's git, and archiving on promotion

**A note, not a specification.** Recorded at the captain's request on 2026-09-17: *"I Think this is
something I probably need to think though and specify more cleanly. save this as a to-do note for me."*
So this is his own to-do, kept verbatim, and promotion out of this note into the specification is his
decision rather than the document's claim.

## What prompted it

Firstmate said the `.gitignore` line he added by hand in `rlp` "stands on its own". His correction:

> that "fix" should have been unecessary.

He is right. A repository needed a manual `.gitignore` edit only because promdance had been left
half-configured, and that is the defect rather than the missing line.

## His words

> The docstrap system should intern promdance directries and create the stores if promdance is
> configured to be "on". Any partial configuration of promdance should be fixed with initializaion or by
> pracitical command options to promdance. promdance is a opt-out compoent of docstrap and that setting
> is for the instaallation or repo by repo project by project in the .docstrap config files. The
> promdance doctrap system should be commiting all and pushing the changes to repmote in promdance.
> there aslo needs to be a system to archive used prompts and spects in the promdance git when they are
> promoted to docs by changing some things in the strapdance header.

## The five things in it

1. **Interning is docstrap's job.** When promdance is on, docstrap interns the promdance directory and
   creates the store. No repository should need a hand-written ignore line.
2. **Partial configuration is a fixable state, not an error to report at.** It is repaired by
   initialization, or by practical command options on `promdance`.
3. **promdance is opt-OUT, not opt-in.** On by default, and the setting lives in `.docstrap` — at
   installation level, and per repository, and per project.
4. **The store commits and pushes itself.** The promdance store is a git repository with a remote, and
   the system commits and pushes to it rather than leaving that to a person.
5. **Promotion archives the source.** When a prompt or spec is promoted into `docs/`, the used original
   is archived in the promdance git, triggered by changing something in the strapdance header.

## What is already known and bears on it

- The store at `~/.local/share/promdance/` is **not a git repository today** — verified 2026-09-17.
  Item 4 is therefore "make it one, then give it a remote", not "add a remote".
- The remote name rule he accepted, with his own hedge *"that rule is fine ... for now"*, is
  `promdance-<machine>` — so `promdance-xomcomen` here — private under `esotericbyte`. The path is
  deliberately not in the name, because the store's location is the XDG data directory for that user on
  that machine and is derivable rather than chosen.
- `ensure_promdance` already creates the store directory and the symlink, and deliberately never
  overwrites a real directory. `gitignore.check` and `gitignore.fix` already exist and are idempotent.
  `find_gitignores_missing_promdance` already detects exactly the case he fixed by hand. None of them is
  reachable from the CLI, which exposes only `backup`.
- `promdance backup` cannot run at its default root at all, so no backup has ever been taken and the
  store's 93 draft files have no safety net.
- His creation sequence, stated 2026-09-15 and unchanged by this note: add to `.gitignore`, create the
  directory in the store, **move** the files there, then create the symlink. The move is what takes them
  out of git, so there is no separate untracking step.
- Item 5 touches `strapdance`'s header vocabulary, where a status is `done` from `done/`, `reusable`
  from `templates/`, `reference` from `memories/` and `notes/`. Which header change means "promoted, now
  archive the original" is not decided.

## What this note does not do

It settles nothing. Items 1 to 3 are close to buildable; item 4 needs the store to become a repository;
item 5 is the one he flagged as needing his own thinking first.

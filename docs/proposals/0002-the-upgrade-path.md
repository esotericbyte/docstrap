# 0002 — An upgrade path, and a loud stop when a version does not match

Written 2026-09-17, answering the captain's question of the same day: *"is there a clear and
systematic upgrade path? if not it needs to be planed out. It occured to me there is a databasae and
some changes will require database migrations. also changes in strapdance voabulary and agent.md
rules or changes in the mcp server could require data changes and agent instruction updates."*

**The answer is no, and the way it fails is silence.** Eight facts, each checked against the working
tree and the live data on 2026-09-17. The last three were not expected and change what the first five
are about:

1. `PRAGMA user_version` is `0` on both `~/.local/share/docstrap/metadata.db` and
   `~/.local/share/docstrap/annotations.db`, and `PRAGMA application_id` is `0` on both. Nothing
   anywhere records a schema version.
2. Every table in `metadata.SCHEMA` and `annotations.SCHEMA` is created `CREATE TABLE IF NOT EXISTS`,
   and `connect()` runs the whole script on every open. An existing database therefore **never gains
   a column**. The code moves on; the data does not; nothing says so.
3. There is no migration machinery of any kind — no runner, no versioned steps, nothing that could
   apply one.
4. The package version has been `0.0.3` across every change in this period, so a version comparison
   could not decide whether a migration were needed even if one existed. §7 treats that as an input
   to this plan rather than a defect to fix here.
5. `scripts/docstrap-stable.sh` is version-aware and data-blind. It reports the version and the git
   ref it installed, and does nothing about the data those versions read.
6. The data is live and there is no backup of either file. `annotations.db` is 16 KB holding one
   annotation. `metadata.db` is 96 KB holding 64 documents, 64 path-history rows, 66 status-history
   rows and 64 content observations — but see the next fact before reading that as 64 documents.

7. **The live database has a second writer nobody declared: the test suite, and it is most of the
   data.** `tests/test_cli_errors.py::test_tag_reports_metadata_error_without_traceback` takes
   `tmp_path` and `monkeypatch` but not the `user_dirs` fixture, so `docstrap tag` runs against the
   *real* `~/.local/share/docstrap/metadata.db`, and `get_or_create_document` inserts a row for a
   `/tmp/pytest-of-johnh/...` path before the monkeypatched failure fires. Every run of the documented
   test command leaves one permanent row behind.

   On 2026-09-17, **59 of the 64 documents came from that one test**, every one of them pointing at a
   `/tmp` path that no longer exists. Five rows are real, and one of those five is
   `/home/johnh/platformshoes/docs/plans/docstrap-mvp.md` — the broken path `docs/roadmap.md` §4.7
   already names. **Four rows out of 64 point at a document that exists.**

   Three consequences, and none of them is cosmetic. It is a defect in that test and it is not fixed
   here. It changes what §3.1's backup is protecting — the file this plan proposes to migrate is
   written by something other than a person using the tool, so "the user knows what is in there" is
   not an assumption a migration may rest on. And those 57 rows are the first customers of
   `docs/roadmap.md` §4.8's orphaned pool: a mechanism designed for exactly this, with a garbage
   collector and a size flag, described before anyone had counted how many rows were waiting for it.
   Whether the first upgrade should also clear them is **Q6** — it is a destructive act on the only
   copy of the data and not this document's to decide.

8. **The status vocabulary in use is narrower than either declared set.** Every one of the 66
   status-history rows carries `draft` (64), `plan` (1) or `proposal` (1) — all three inside
   `metadata.VALID_STATUSES`, and none of them a strapdance directory value. So the two-vocabulary
   divergence of §4.4 is real in the code and has **not yet reached the data**. That is what makes Q1
   answerable cheaply now and expensive later.

**This document is in `proposals/` and not `plans/` because the captain has not evaluated it.** The
folder carries the weight (repository `AGENTS.md`). It keeps the plan number-line rather than starting
a second one, so promotion is a move between folders and not a renumbering — which is how
`docs/spec.md` reached `docs/plans/` (its Q1).

**Nothing here has been implemented.** No migration runner exists, no schema changed, no version was
stamped, and the live databases were read for their schema and otherwise not touched.

**A fifth axis arrived while this was being written.** The captain named four; on the same day the
promdance store became a git repository with a remote (`docs/spec.md` §8.4), which is a third
persistent state beside the two databases and carries the same question in a different shape. §12 is
its section, and §2 explains why it could be added rather than retrofitted.

## §1 What already does this, and what was rejected

The captain's method, applied first: **look at what comparable tools and docstrap's own dependencies
already do**, on the expectation that machinery may be unneeded. docstrap is an integrator, and an
existing migration library it can drive beats one written here. The precedent in this workspace is
`docs/plans/2026-06-poetry-to-uv-migration.md` §4, which replaced the homegrown `dpo migrate
tool-swap` with `uvx migrate-to-uv` for exactly this reason.

Applied here, the method returns **no library** — but the reasoning is below rather than asserted, and
one thing worth borrowing turned up in the dependency tree already.

### §1.1 What is already in the tree

There is no ORM and no migration tooling. `uv tree --package docstrap` resolves 105 packages and
contains no SQLAlchemy, no Alembic, no ORM of any kind. Both database modules use the standard
library's `sqlite3` directly, with raw SQL and `sqlite3.Row`.

Two things in the tree are relevant anyway.

1. **Sphinx already implements the mechanism this plan needs**, and docstrap depends on Sphinx.
   `sphinx/environment/__init__.py` declares `ENV_VERSION = 66` with the comment "This is increased
   every time an environment attribute is added or changed to properly invalidate pickle files."
   `_get_env_version()` builds a **mapping** — `{'sphinx': 66, '<extension>': n, ...}` — so each
   extension versions its own contribution to the stored state independently. `BuildEnvironment.setup`
   compares with `!=`, not `<`, and raises `BuildEnvironmentError('build environment version not
   current')`; `Sphinx._load_existing_env` catches it, logs the reason, and builds a fresh environment.

   Three properties of that design transfer directly: a hand-bumped monotonic integer, a mapping of
   independent contributors rather than one number, and an **exact-match** comparison so a *newer*
   stored version is refused as loudly as an older one. The remedy does not transfer — Sphinx's store
   is derived and can be thrown away, while `metadata.db` holds 66 status transitions and 64 ULIDs
   that cannot be rebuilt from the tree. Copy the shape, not the response.

2. **`packaging` is present transitively** (via `sphinx` and `pytest`), so `packaging.version.Version`
   is available for comparing `x.y.z` — but transitively, which means declaring it if used. §7 is why
   this plan does not need it.

### §1.2 The libraries considered, and why each was rejected

1. **Alembic 1.20.0** (released 2026-09-11) requires `SQLAlchemy>=2.0`, `Mako` and
   `typing-extensions`. docstrap writes raw SQL against `sqlite3`; adopting Alembic means adopting an
   ORM stack solely for migration bookkeeping, and then owning `alembic.ini`, an `env.py` and a
   `versions/` directory. Five tables and a handful of DDL statements do not pay for that.

2. **yoyo-migrations 9.0.0** carries no SQLAlchemy — `sqlparse`, `tabulate`, `importlib-metadata` —
   which is much lighter, but it was **last released 2024-08-10**, two years stale. The disqualifying
   property is its model rather than its dependencies: migrations are *files on disk discovered at
   runtime*. docstrap's schema is one Python constant that ships inside the wheel, and a
   wheel-installed tool that must also find a migrations directory has a second install surface to
   keep correct. That is the class of defect `docs/spec.md` §4 and the one-owner rule exist to prevent.

3. **caribou 0.6.0** (released 2026-02-06) is the closest fit and the most instructive rejection.
   Zero runtime dependencies, SQLite only, 351 lines in one module. It was rejected on one specific
   behaviour, read out of its source: `Database.upgrade` sorts the migrations, then
   `if current_version <= database_version: continue`. A database at a version **newer** than any
   migration the code knows about therefore skips every step and returns with no error — the exact
   silent failure this plan exists to remove. Adopting caribou would mean wrapping it in the check it
   does not perform, at which point the wrapper is the mechanism and caribou is contributing file
   discovery docstrap does not want. Two further costs: it tracks version in its own
   `migration_version` table rather than in `PRAGMA user_version`, and its version *is* a timestamp
   parsed out of a filename, which is a second rule that turns text into an identifier.

4. **sqlite-utils 4.2.1** is a schema-manipulation toolkit — `add_column`, `transform` — not a
   migration runner. It would supply verbs, not versioning, and brings `click`, `pluggy`,
   `python-dateutil`, `sqlite-fts4`, `tabulate` and `pip`.

5. **Django migrations and sqlalchemy-migrate** are not applicable: both presuppose an ORM docstrap
   does not have and will not acquire for this.

### §1.3 The honest conclusion: hand-rolled, and small

Every library surveyed brings a **migration repository** — a directory of migration files discovered
at runtime — and that is the part docstrap does not need and should not acquire. What docstrap needs
is three things: somewhere to write a number, a rule for comparing it, and a loud stop.

SQLite supplies the first for free. `PRAGMA user_version` is a documented 32-bit slot in the file
header reserved for the application, which is what Firefox, Chrome and Signal use for this. It costs
no table, survives `VACUUM`, and reads `0` on a fresh file with no bootstrap — unlike a
`schema_version` table, which you must create before you can ask what version you are at, which is a
write to a database whose version you have not checked.

The second and third are roughly forty lines, and they are the forty lines every library above gets
wrong in at least one direction.

**No dependency is proposed.** If one were, this section would say what it costs to own; the point of
doing the survey was that the answer came back "nothing to own", and that answer is only worth
anything because the survey was real.

One piece of machinery a library *would* have given free must therefore be written by hand, and §9
puts it in the first step for that reason: a test that a database built fresh from `SCHEMA` and an
empty database migrated through every step end with identical `sqlite_master`. Without it the two
drift, and the drift is invisible until someone's data is on the wrong side of it.

## §2 The version manifest — six contributors, not one number

The axes drift **independently**. A single number would move for all of them and mean nothing for any
of them. So the scheme is a manifest of named integers, in Sphinx's `_get_env_version` shape: each
integer is declared by the module that owns the thing it versions, and a new contributor can be added
without renumbering the others.

That property was tested within a day of this being written. The captain named four axes on
2026-09-17; the promdance store became a git repository with a remote later the same day, which is a
**third persistent state** beside the two databases and has the same question in a different shape.
It is the sixth row below and §12 is its section — added, not retrofitted, which is the whole reason
the manifest is a set of names rather than a number.

| axis | version declared in | recorded where | compared by |
|---|---|---|---|
| metadata schema | `metadata.SCHEMA_VERSION` | `metadata.db`, `PRAGMA user_version` | `metadata.connect` |
| annotations schema | `annotations.SCHEMA_VERSION` | `annotations.db`, `PRAGMA user_version` | `annotations.connect` |
| strapdance vocabulary | `strapdance.VOCABULARY_VERSION` | a column on the rows written under it (§4) | doctor, the write commands |
| instruction set | the packaged skills' front-matter (§5) | a project's own `.docstrap` | doctor, `docstrap init` |
| promdance store layout | `storegit.LAYOUT_VERSION` (§12) | a trailer on the store's own commits | doctor, `promdance status` |
| MCP contract | not built — `CONTRACT_VERSION` when it is (§6) | announced by the server | its clients |

They are **monotonic integers, not `x.y.z`**, and not the package version. §7 is why.

### §2.1 The two databases version apart

`docs/spec.md` §6 already decided this for a different reason and the reason still holds: annotations
live in a separate *file* rather than separate tables "so annotations can be backed up, migrated, or
replaced independently of metadata." Each file carries its own `user_version`.

A shared number would move `annotations.db` for a change to `documents`, and force a user through an
upgrade of a 16 KB file holding one row in order to gain a column in a different file. Versioning
apart costs one extra integer and one extra line in the doctor report, and buys the property the file
split was made for.

### §2.2 `application_id`, once

Both files read `application_id = 0` today, which means "not stated". Setting it once to a fixed
docstrap constant costs a single write and lets `file`, and any future recovery, say *this is a
docstrap metadata database* rather than *this is a SQLite database*. It is the standard companion to
`user_version` and there is no reason to leave it empty.

## §3 What happens when the versions do not match

Today all three cases below are one case, and that case is silence. Each needs its own stated
behaviour.

### §3.1 Behind — `stored < expected`

This is the common case, and it is the case that exists the moment anything in `SCHEMA` changes.

**docstrap refuses to open the database and says exactly what it would do.** It does not migrate on
open.

The reason is the rule the captain set for builds, applied to data. A build never writes into a
project tree, so a build cannot surprise you by changing your repository. By the same logic, an
ordinary read command must not rewrite the user's only copy of their history. Auto-migration on open
means `docstrap questions` — a read-only report — silently restructures every row of a user's
metadata because it happened to be the first command run after an install. The user finds out
afterwards, which is this plan's own failure mode moved one step later.

So every entry point that opens a database checks first, and on a mismatch exits with a message
naming the file, the stored version, the expected version, the command that fixes it, and the fact
that **nothing has been changed**. One command migrates: working name `docstrap upgrade` (no such
command exists today; `docstrap status` is already taken and means a document's lifecycle status). A
person runs it deliberately, it is the only thing in docstrap that writes a schema change, and it is
the only place migration code is reachable from.

**The backup is not a flag.** `metadata.db` has no backup and holds history that cannot be
reconstructed from the tree. `docstrap upgrade` copies to `metadata.db.<stored-version>.bak` before
the first statement, using SQLite's own `Connection.backup()` — consistent under WAL, no new
dependency — and refuses to proceed if the copy fails or if a backup at that name already exists.

Opening fact 7 is why this is not over-caution. The file is already written by something other than a
person using the tool — 59 of its 64 document rows — so "the user knows what is in there" is not an
assumption a migration may rest on.

### §3.2 Ahead — `stored > expected`

A rollback creates this: install `docstrap-v0.0.5`, run it once, then
`scripts/docstrap-stable.sh install docstrap-v0.0.4`.

**docstrap refuses, permanently, and never migrates down.** The message names both versions and says
which install can read the file — which it can say, because the stored number is right there.

Three reasons, and the first is sufficient. A down-migration by definition discards information the
newer schema held, so it is a data-destroying operation wearing the clothes of a repair. Second,
writing one doubles the migration work forever and the second half is never exercised, because a user
who rolls back usually rolls forward again. Third, the real remedy already exists and is one line:
reinstall the newer docstrap, which `docstrap --version` and the stable installer already make easy
to identify and perform.

Note that the comparison is `!=` **before** it is `<` or `>`. Sphinx's `!=` is what catches this case
at all; a `<` check alone makes it silent, which is precisely caribou's behaviour and precisely why
caribou was rejected (§1.2(3)).

### §3.3 Version 0 — three files that look alike

`user_version = 0` is ambiguous today, and the first migration has to resolve it. A brand-new empty
file reads 0; so does the live 94 KB database. The distinguisher is the data, and there are three
outcomes:

1. **Version 0 and no tables** — a fresh file. Create from `SCHEMA` and stamp it at the current
   version. No migration runs.
2. **Version 0 and docstrap's tables present** — today's live database. Stamp it version 1 and
   **change nothing else**.
3. **Version 0 and tables that are not docstrap's** — refuse, and touch nothing. This is somebody
   else's file at docstrap's path.

Outcome 2 is the whole of migration 1, and it is worth saying plainly: **the first upgrade any user
ever runs cannot lose anything, because it changes no data.**

### §3.4 What a migration step is

A function in an ordered tuple beside `SCHEMA` in the module that owns the database:

```python
MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "stamp the pre-versioning schema", _m1_stamp),
)
```

Each step takes a connection, runs inside one transaction, and steps are applied in order from
`stored + 1` to `SCHEMA_VERSION`. `SCHEMA` stays exactly what it is — what a *fresh* database gets —
and `CREATE TABLE IF NOT EXISTS` stays correct in that role. What changes is that it stops being the
only thing that runs.

The equivalence test of §1.3 is what holds the two together: fresh-from-`SCHEMA` and
migrated-from-empty must produce identical `sqlite_master`. It is the only real machinery this plan
asks for, and §9 puts it first, when there is one trivial migration to test it against.

## §4 The strapdance vocabulary

The hardest of the four axes, and the answer is mostly *do less*.

### §4.1 What a vocabulary change actually changes

The tables are `KIND_BY_DIRECTORY`, `STATUS_BY_DIRECTORY`, `HOLD_DIRECTORY` and `DEFAULT_STATUS` in
`strapdance.py`. They are **resolution rules, not stored values**, and the reader never writes — the
module says so three times and it is the property the whole standard rests on. So a vocabulary change
does not, by itself, alter a single stored byte.

What it alters is the **meaning** of bytes already stored, in one place: `documents.current_status`
and `status_history.status` in `metadata.db`, written by commands that took a value the vocabulary
produced. Sixty-six such rows exist today, of which two carry a value other than `draft` (fact 8).

Three kinds of change, and they are not alike.

1. **A directory name is added.** `KIND_BY_DIRECTORY` gains `"pitches": "pitch"`. Nothing stored
   changes meaning; documents that used to resolve to kind-unknown now resolve. There is nothing to
   migrate. The vocabulary version moves so the report can say *these values were resolved under
   vocabulary 3 and this is 4* — a statement, not a repair.
2. **A value is renamed.** `reusable` becomes `template`. A stored `reusable` now means something the
   new vocabulary has no word for.
3. **A value is removed** with no replacement.

### §4.2 A vocabulary migration reports; it never rewrites

For cases 2 and 3 there is one rule, and it is the captain's, set on 2026-08-28: **an asymmetry is a
finding, never a repair.** In his words, "IF one status is present and the other is missing that is
not a signal to copy the filled one to the other one. that is a sign that the procedures were not used
reasonably." `docs/spec.md` §5.1(2) already states the general form: an asymmetry is "reported as a
finding, never silently backfilled."

The principle underneath is that a recorded value is **evidence of what happened**, and a tool that
rewrites it destroys that evidence in order to make its own tables tidy. A migration that quietly
turned 66 stored statuses into their new spellings would produce a database that agreed with itself
and no longer recorded anything.

So a vocabulary migration is a **report**, and it is `docstrap doctor`'s report. For every stored
value the new vocabulary does not contain: one finding naming the document, the value, when it was
written, and the vocabulary version in force when it was written. That is the shape doctor already
has for `Ambiguity`. And the remedy is the shape doctor already has for it too: `--fix-plan` writes a
script nobody has run, one proposed `docstrap status <path> <new-status>` per finding, **commented out
unless a person named the destination**. Doctor needs no new mechanism for this; it needs a second
kind of finding.

### §4.3 What the vocabulary version is for

Not to drive a rewrite — to make the report truthful. Today a stored `reusable` is indistinguishable
from a value that was never valid. With the vocabulary version recorded beside it, docstrap can say
*this was correct when it was written and the vocabulary moved underneath it*, which is a different
and truer sentence than *this is wrong*.

**Where it is recorded:** one new column, `vocabulary_version INTEGER`, on `status_history`, and
denormalised onto `documents` in the same way `current_status` already is. It is written at the moment
a status is written, by whichever command wrote it.

Rows written before the column existed hold NULL, and **NULL is its own state, not a synonym for
version 1.** The precedent is exact and it is the captain's: `docs/spec.md` §8.1.3's tri-state
`submitted` field, where absent means "written before the distinction existed", is never written back,
and lets untouched legacy rows survive a rewrite byte for byte. NULL here means "written before
docstrap recorded which vocabulary was in force", and doctor reports it as unknown-provenance rather
than guessing. One new column, one nullable value, and a convention the corpus already has rather than
a second one.

### §4.4 A prerequisite this plan cannot settle

There are **two status vocabularies in the code right now**, and §5.1 says there is supposed to be
one. `metadata.VALID_STATUSES` is the closed set `{draft, proposal, spec, plan, active, archived}` and
rejects anything else on write. `strapdance.STATUS_BY_DIRECTORY` resolves to `done`, `reusable` and
`reference` — none of which is in that set — so a document in `notes/` resolves to a status
`metadata.set_status` would refuse. §5.1 is a rule ahead of the code rather than a description of it.

This blocks the vocabulary axis and nothing else: the first vocabulary version cannot be declared over
a set that is about to change. It is **Q1**.

## §5 AGENTS.md rules and agent instructions

### §5.1 What docstrap ships, and what it only expects

**Ships:** two skill files, `docstrap-authoring.md` and `docstrap-lifecycle.md`, packaged inside the
wheel and copied by `docstrap init` into `~/.claude/skills/`. That is **user-level, not per-project**.
`cli._install_claude_skills` compares bytes: identical is skipped, different prompts before overwrite.

**Only expects:** the conventions an adopting project's own `AGENTS.md` must carry for docstrap to
work. The load-bearing one is the `Q<n>` label — `questions.py` finds a document's questions by that
label alone and interprets no question mark, so an unnumbered question is *invisible* to the tool.
The plans/-versus-proposals folder weight and the stale-text rule are in the same category. Nothing
connects any of them to a docstrap version.

Two hard constraints bind everything below. **Firstmate never writes a project's `AGENTS.md`** — the
tool does, through the project's own delivery path. And a build never writes into a project tree, so
whatever updates instructions is **an explicit command a person runs, never a side effect**.

### §5.2 Version the skills docstrap already ships

Each packaged skill's front-matter gains `docstrap_instruction_version: <n>` — a monotonic integer,
bumped when the instructions change in a way an adopting project must **act on**, not for a typo.
`docstrap init` reads the installed copy's number and compares.

This replaces a byte comparison that cannot tell *the user edited this* from *this is three releases
old*: today both are "not identical, prompt". With a version it can distinguish them and say each
differently.

The install stays exactly as cautious as it is. It still prompts before overwriting, and it never
overwrites a file whose version equals the packaged one even when the bytes differ — that is a local
edit, and clobbering local edits is the failure mode of every dotfile installer ever written.

### §5.3 A project declares what it was written against

One optional key in the project's own `.docstrap` file:

```yaml
instruction_version: 4
```

`.docstrap` and not `AGENTS.md`, for a reason worth stating. `AGENTS.md` is prose a person owns;
putting a machine-read number into it makes a tool a co-author of a file it should only ever read.
`.docstrap` already exists, is already docstrap's, is already in the project's git, and is already the
machine-readable declaration of how docstrap relates to this project — which is exactly what an
instruction version is.

Absent is its own state, the third use of that pattern after `submitted` and `vocabulary_version`: it
means the project predates the declaration, and is reported as *not declared* rather than as version
zero.

### §5.4 How a project learns it is stale, and how it is updated

It **learns** from `docstrap doctor`, which already walks the workspace and already reports per-project
findings. One line per project whose declared `instruction_version` is behind the running docstrap's,
naming both numbers and what changed between them. The projects come from the registered stores
`user_config` already knows about, so doctor does not grow a second way to find them.

It is **updated** by an explicit command a person runs — working name `docstrap instructions update
[PATH]` — and that command does not write `AGENTS.md` either. It produces a **derivative beside it**,
exactly as every other docstrap tool does: nothing is altered in place, tools produce a derivative
beside the original, and that is what makes it safe to point docstrap at a clone, a read-only
checkout, or someone else's repository.

*What* the derivative is — a proposed diff, a block to paste, an `AGENTS.md.docstrap-proposed` beside
the file, or a fix-plan script in doctor's existing shape — is **Q3**. All four are defensible and the
choice is the captain's. What is not open is that it produces something a person then applies.

The three-way split that makes this honest: docstrap **ships** instructions (the skills, versioned,
installed to the user's own directory with consent), **expects** conventions (the `Q<n>` label, which
a person puts in their project's `AGENTS.md`), and **reports** the gap. It never closes the gap itself.

## §6 The MCP server — a forward requirement, not a design

Not built. `docs/roadmap.md` §4.10 records the captain's decision of 2026-09-12 to build it with
FastMCP, and states the boundary that makes this axis cheap: "MCP is a transport over capabilities
that already exist or are already specified, never a parallel copy of them."

That boundary is why an MCP server costs this plan almost nothing, and the plan should show it rather
than assert it. An MCP client is a consumer whose expectations can drift from the data — and so is the
browser instrument, and so is the CLI. All three reach the data through the same owners. The version
check of §3 lives in `metadata.connect` and `annotations.connect`, which is **beneath** all three
surfaces, so an MCP server that opens a database behind its version gets the same refusal an agent's
`docstrap questions` gets, for free, because it comes through the same door.

Three things the scheme must leave room for, and does.

1. **A sixth contributor.** §2's manifest is a set of named integers rather than one number precisely
   so a new one can be added without disturbing the others. `CONTRACT_VERSION` slots in beside the
   five.
2. **A consumer that cannot see the files.** An MCP client may be on another machine. So the version
   report must be **reportable over the wire**, not only raised as a process exit — which is why §8's
   report is a data structure first and a terminal rendering second, the shape `DoctorReport` already
   has. A scheme surfaced only by a CLI exit code would foreclose this.
3. **A client pinned to an older contract.** §3's three cases apply unchanged, with the same answer
   for ahead: refuse and name the version, never serve a degraded response. How the server *does* that
   is its own design decision when it is built.

Nothing above designs the server, and nothing above should be read as scheduling it.

## §7 The package version is an input, not a mechanism

Named because the brief requires it named, and deliberately not solved here.

`0.0.3` has been the version across every change in this period. That is not a defect in the number —
it is `VERSIONING.md` §2.3 working exactly as written: "bump when you want to name a state you can go
back to and install", and no state has been named, because §6 of that document records that **no
release tag exists in the repository at all**. The version is honest. It is simply not a clock.

The consequence for this plan is precise and limited: **the package version cannot be the trigger for
a migration, and this plan does not use it as one.** The five integers of §2 are their own number-line
for that reason. They move when the thing they version changes, which may be twice between two
releases or not at all across five. A scheme keyed on `x.y.z` would force a package bump for every
schema change, turning §2.3's one clear trigger into two competing ones.

What is *not* settled is whether a schema change should nonetheless force a release bump, so that
"which docstrap can read this database" has an answer a human can act on — §3.2's refusal would like
to say "install docstrap 0.0.6 or later", and it can only say that if a schema version maps to a
release. Against: it re-couples the two number-lines this section just separated. A third option gets
the message without the coupling — the migration step records the package version it ran under, as
data, without the package version driving anything. This plan is written so all three stay possible.
It is **Q4**.

## §8 Where a user finds out where they stand

`docstrap doctor`, extended. Not a new command.

Doctor is already the "report and propose, never act" surface — its own module docstring: "It reports
and proposes. It never acts." It already walks the workspace, already renders findings with the
provenance that produced them, already distinguishes document findings (`Ambiguity`) from environment
findings (`FirstmateFinding`), and already writes a fix-plan script nobody has run. Every one of those
properties is what a version report needs. Version findings join the environment half.

Two traps, both cheap to avoid now and expensive later.

1. **Doctor must report a version mismatch without tripping over it.** Doctor opens no database today.
   Under §3, opening one at the wrong version refuses. So the version read must be a separate
   non-opening read — `PRAGMA user_version` on a connection that does not run `SCHEMA` — exposed as
   its own function. Otherwise the one command whose job is to tell you what is wrong becomes the one
   command that cannot run.
2. **The report is a data structure first.** §6(2) needs it over the wire, and `DoctorReport` is
   already shaped that way. Rendering is a second step, as it already is.

What the section looks like:

```
versions
  metadata.db        schema 1, expected 3   BEHIND — run `docstrap upgrade`
  annotations.db     schema 1, expected 1   ok
  strapdance vocab   in force 2             12 of 66 stored statuses were written under
                                            an earlier vocabulary; 0 hold a value this
                                            vocabulary does not contain
  instructions       packaged 4
    platformshoes    declared 4             ok
    dkp              not declared           predates the declaration
    trk_tdp          declared 2             BEHIND by 2
```

`docstrap --version` already answers the sixth line — version, install kind, ref and commit — and is
left alone.

## §9 Ordering

### §9.1 What is independent

**The annotations database.** One table, one row, its own file, versioned apart by §2.1. It could be
done entirely alone, and it is the smallest possible full rehearsal of the mechanism.

**The instruction axis (§5).** Nothing in it touches SQLite. It is blocked only on Q3, and there is a
real case for doing it first: it has the most adopting projects and the least data at risk.

**The promdance store (§12).** Also nothing to do with SQLite, and the only axis whose backup already
exists, because git is it. §12.4 is why adding a third persistent state did not move anything here.

### §9.2 What must be sequenced

1. **The manifest and the three-case rule (§2, §3) come first.** Everything else either records a
   version or reports one, and neither can be built against a scheme that does not exist. It is also
   the only piece that is urgent in the ordinary sense — it is what makes today's silent failure loud.
2. **The stamping migration (§3.3, outcome 2) is inside step 1 and cannot be separated from it.**
   Version 1 exists to say "this is today's schema". There is no version 1 without it.
3. **The vocabulary axis (§4) is blocked on Q1** and on nothing else. Answered, it runs in parallel
   with the instruction axis. Unanswered, it cannot start.
4. **The doctor report (§8) comes last**, because it reports on every other axis. It can be built
   incrementally — the database section as soon as step 1 lands, the store section whenever §12's
   trailer exists — but it is not finished until they are.
5. **The MCP axis (§6) is not in this sequence.** It is a constraint on the others, satisfied by §2's
   shape and §8's data-first report, and it is checked rather than built.

### §9.3 What must not be interleaved

**The stamping migration and any schema change.** Version 1 changes nothing; version 2 is the first
that changes something. Landing them together makes the first upgrade a user ever runs one that can
lose data, and the entire reason for doing the stamp separately is that it cannot.

## §10 The first step, if this were dispatched tomorrow

**`PRAGMA user_version` is read and compared, nothing is migrated, and a mismatch stops the program.**

Concretely: `SCHEMA_VERSION = 1` declared in `metadata.py` and in `annotations.py`; `connect()` reads
`user_version` before it runs `SCHEMA` and raises on `!=`; §3.3's three-way discrimination handles the
`0` it will find on every existing file; `application_id` is set; and `docstrap upgrade` exists
carrying exactly one migration — the stamp, which changes no data and takes a backup anyway.

Four reasons this one and not the others.

1. **It is the only step that reduces risk that is live right now.** The other three axes describe
   drift that has not happened yet. This one describes a database on disk with 64 document rows and
   66 status transitions that will silently disagree with the code the next time `SCHEMA` changes — and
   the roadmap already has two such changes written down. §4.7 (metadata that survives a move) and
   §4.8 (the orphaned pool, which needs a state a row can be in) both require schema changes and
   currently have nowhere to put one.
2. **It is the smallest thing that can be wrong in a way that is found.** After it, every subsequent
   schema change is a numbered step with a test behind it. Before it, every subsequent schema change
   is another silent divergence.
3. **It cannot lose data, by construction.** The only migration it ships changes nothing.
4. **It unblocks §4.7 and §4.8**, which are the two roadmap deliverables most obviously waiting on it.

And one thing to do *inside* that step, because it costs an hour there and is never written later: the
fresh-versus-migrated equivalence test of §1.3, written while there is exactly one migration and it is
trivial. It is the test nobody writes at migration seven, and it is the one that makes every migration
after seven safe.

## §11 What this forecloses

Every versioning scheme forecloses something. Seven things, each accepted.

1. **Opening a docstrap database with any other tool becomes a versioned act.** Today `sqlite3
   metadata.db` works and always will; afterwards, a script that opens the file and writes to it is
   writing at a version it did not check, with no excuse. `docstrap-lifecycle.md` already forbids this
   — "Never write to the databases", and `sqlite3`, are both asserted by a test — and this makes the
   prohibition load-bearing rather than advisory. The cost is real: ad-hoc repair by hand gets harder,
   deliberately.

2. **A schema change stops being free.** Today it is editing a string. Afterwards it is editing a
   string, writing a migration step, bumping an integer and satisfying the equivalence test. That is
   the intended cost and it is still a cost — small schema changes will feel disproportionate, and the
   temptation will be to add a column to `SCHEMA` without a step. The equivalence test is what catches
   that, which is why §10 puts it first.

3. **Downgrade is gone, by decision.** §3.2 refuses rather than reverses, so an install moves forward
   through versions and never back, and testing a change against the live database means copying it
   first. The stable installer makes rolling the *code* back easy, which makes this asymmetry more
   noticeable rather than less. Accepted, because a down-migration written and never run is worse than
   no down-migration.

4. **The vocabulary can never be silently corrected.** §4.2's report-never-rewrite means a renamed
   status value leaves findings in the doctor report until a person acts on each one, and there will
   be no bulk fix. At 66 rows that is comfortable; the design says it stays right at any size, and if
   it ever is not, the answer is a better fix-plan script, not an automatic rewrite. This forecloses
   convenience on purpose, and it is the captain's constraint rather than a design preference.

5. **Absence keeps accumulating meaning.** This plan makes two more things tri-state where absent is
   its own value — `vocabulary_version` and `instruction_version` — joining `submitted`. Each is
   individually right and the pattern is already established. What is foreclosed is ever treating NULL
   in these columns as a default, and the more columns carry that rule the more places a future
   contributor can get it wrong. The mitigation is documentation and nothing else, which is why it is
   named here.

6. **`user_version` is spent.** It is one 32-bit integer per file. Using it for the schema version
   means it cannot later hold anything else, and a second per-file number would need a table after
   all. Almost certainly fine — it is what the slot is for — but it is a one-way door.

7. **The store's commit messages stop being free text.** §12.2 puts the layout version in a trailer,
   which means `storegit.commit_all`'s message is now partly machine-read. Anything that writes a
   store commit by another route — a person running `git commit` in `~/.local/share/promdance/`, which
   is an ordinary thing to do in a git repository — writes a commit with no trailer, and §12.2(3)'s
   *absent* then has two meanings rather than one. The mitigation is that absent is read from the
   newest commit that **has** a trailer rather than from the newest commit, and that is a rule
   somebody has to remember. Named because it is the one place this plan makes a human action
   slightly wrong.

## §12 The promdance store — a third state, where git is already most of the answer

Written after the rest of this document, when `docs/spec.md` §8.4 landed on 2026-09-17 and made the
promdance store at `~/.local/share/promdance/` a git repository with a remote. It is a **third
persistent state** beside the two databases, it has the same question in a different shape, and the
honest answer for it is *less* machinery rather than more — for one reason that is worth stating
before anything else.

**Git is already the backup §3.1 has to build by hand.** The databases have no copy of any kind, which
is why `docstrap upgrade` must take one before its first statement. The store has history, and once a
user hands over a URL it has an off-machine copy as well. So the expensive half of the database plan
is, for this axis, already done by a tool docstrap drives rather than reimplements.

### §12.1 Three ways this axis is not the database axis

1. **There is no schema and no header to stamp.** The store is a directory of slug-named directories,
   and `docs/spec.md` §8.4.2 is emphatic that initialising "adds `.git/` and nothing else" — **no file
   is written in among the drafts**, not a `.gitignore`, not a README, nothing. So the obvious move,
   a `.docstrap-store-version` file at the root, is forbidden by a rule that exists for a good reason:
   every entry beside `.git/` is a draft or a draft's directory, and the moment that stops being true
   the store stops being self-describing.

2. **It has a distribution channel the databases never had.** Two machines are two stores —
   §8.4.1 derives the suggested name from the host precisely because "what a name has to distinguish
   is *machines*" — and a remote can join them. So a store written by a newer docstrap on one machine
   can be pulled by an older docstrap on another, and **git will merge it without an opinion**, because
   git has none about what version wrote a file. §3.2's "ahead" case stops being only a rollback
   artefact and acquires an ordinary route.

3. **Its formats already evolve in-band, successfully.** `answers.md` has no version key and never
   needed one: the tri-state `submitted` field of §8.1.3 carried a real format change by making
   absence its own state and never writing it back, so the ten real answers in the store survived a
   rewrite byte for byte. That is the same technique §4.3 and §5.3 reach for, and here it has already
   been proved on live data.

### §12.2 What follows: a layout version, in a commit trailer

The store needs one integer — `storegit.LAYOUT_VERSION` — and it versions the **layout**: what a store
entry is, how it is named, and what a project's symlink points at. Not the drafts, which are prose
docstrap does not parse, and not `answers.md`, which §12.1(3) says evolves in band.

**It is recorded as a trailer on the store's own commits.** `storegit.commit_all` already takes a
`message` parameter and defaults it to `"Commit promdance drafts"`; a trailer appended there writes no
file into the tree, so §8.4.2 holds, and it travels with the commit, so a machine that pulls the store
can read it with `git log`. `.git/config` was the other candidate and is wrong for exactly the reason
the trailer is right: it is a local fact that does not travel, and travelling is the whole problem
here.

**The comparison is not §3's.** A database is opened and refused; a store is a working directory that a
person's drafts live in, and refusing to open it would mean refusing to save a draft. So:

1. **Behind** — the running docstrap reads a store whose newest layout trailer is older than
   `LAYOUT_VERSION`. Report it in doctor and in `promdance status`, and carry on. A layout change is a
   file move (§12.3), and nothing about reading or writing a draft depends on it.
2. **Ahead** — the trailer is newer. **Report loudly and refuse to `commit` or `push`**, while still
   allowing reads. That is the narrowest refusal that prevents the actual damage, which is an older
   docstrap committing a rearranged store back over a layout it does not understand and pushing it to
   the remote both machines share.
3. **Absent** — no trailer anywhere in the history, which is every store today including the
   captain's, whose first commit predates this. Absent is its own state, as everywhere else in this
   plan: it means *written before docstrap recorded a layout*, and it is reported as that rather than
   treated as version 1.

### §12.3 A layout migration is a move, and the store already decided how those go

The store's own precedent is `docs/spec.md` §8.6: a project that already holds a real `promdance/`
directory needs its files **moved** into the store, and `promdance intern` **never moves a file** —
such a project is "reported and left exactly as found, every time". Roadmap §4.15 carries the work and
names the shape it must take, borrowed from chezmoi: show exactly what would move before moving it,
per-project rather than as a sweep, and refuse when the destination already holds content.

That is the same answer §4.2 reached for the vocabulary and §5.4 for the instructions, arrived at
independently and before this plan existed. So the store axis needs no new mechanism at all: a layout
migration is reported by doctor, performed by an explicit per-project command, and shown before it is
done. What this plan adds is only the **number** that lets the report say which layout a store is on.

### §12.4 The store is the reason the ordering in §9 does not change

It might look like a fourth thing to sequence. It is not, for two reasons. It is independent of every
database axis — nothing in it touches SQLite — so it sits beside the annotations database in §9.1.
And its expensive prerequisite, a backup, is the one thing it already has.

It also supplies a second, independent confirmation of fact 7. `docs/spec.md` Q7 asks about
`isolated-tool-store` and `markdown-store`, two store entries "written by docstrap's own test suite
rather than by anybody drafting", and answers the question this plan asks in Q6 the same way: it is
not an agent's call, because "'it looked empty' is precisely the reasoning that should never be enough
to delete something there." Two of the three persistent states carry test-written rows that nobody
meant to keep, found independently on the same day. That is a pattern rather than two accidents, and
it is **Q7** below.

## Open questions

Numbered so `docstrap questions` finds them, separately from the section numbers above. None is
answered here; each is the captain's.

**Q1.** `docs/spec.md` §5.1 states one shared status vocabulary, but `metadata.VALID_STATUSES` holds
`draft, proposal, spec, plan, active, archived` while `strapdance.STATUS_BY_DIRECTORY` resolves to
`done`, `reusable` and `reference`, none of which is in that set. Is the metadata set the one
vocabulary, with the strapdance directory mappings to be brought into it? (§4.4 — this blocks the
vocabulary axis and nothing else.)

**Q2.** §3.1 refuses to open a database that is behind, on every command. Should the read-only
commands — `questions`, `doctor`, `--version` — be exempted and allowed to run when they touch only
tables the old schema already had?

**Q3.** §5.4's update command produces a derivative rather than editing a project's `AGENTS.md`.
Should that derivative be a fix-plan script in `docstrap doctor --fix-plan`'s existing shape, rather
than a proposed file beside `AGENTS.md`?

**Q4.** §7 keeps the schema versions and the package version on separate number-lines. Should a schema
change nonetheless force a package version bump, so §3.2's refusal can name the docstrap release that
can read the file?

**Q5.** §2.1 versions the two databases apart and gives both the same refuse-and-migrate treatment.
`annotations.db` holds one row against a store `docs/spec.md` §6 calls complete and unexercised.
Should it get that same treatment, rather than the cheaper rule that a version mismatch may recreate
it?

**Q6.** Fact 7: 59 of the 64 document rows in the live `metadata.db` were written by one test and
point at `/tmp` paths that no longer exist. Should the first upgrade also clear them — a destructive
act on the only copy of the data, which is why it is asked rather than planned — or should they be
left for `docs/roadmap.md` §4.8's orphaned pool to collect when that is built?

**Q7.** Two of the three persistent states were found on 2026-09-17, independently, to hold rows
nobody meant to keep, both written by docstrap's own test suite: 59 document rows in `metadata.db`
(fact 7) and the two empty store entries `docs/spec.md` Q7 asks about. Is a test that writes to live
user state a defect class worth a standing rule — a suite-wide assertion that no test touches a real
XDG directory — rather than two separate cleanups?

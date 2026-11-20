# 0006 — firstmate and docstrap through a Claude Code skill and an MCP server

Proposal, written 2026-10-31. Under evaluation and not approved. It replaces the firstmate-docstrap
bridge that lives in the firstmate fork with an MCP server that docstrap owns and a Claude Code skill
that tells any session when and how to use it. It folds in five earlier firstmate records, and §15
says where each of their questions stands.

## Contents

1. Purpose
2. The Claude Code seams this design stands on
3. What exists today
4. The client and its space
5. The MCP server
6. The skill
7. The question surface
8. Question handles
9. References
10. Clean-up
11. What the fork code does today, and where each piece goes
12. Migration from the fork bridge
13. Stages
14. Architecture and tradeoffs
15. The folded records and their questions
16. Open questions

## §1 Purpose

Firstmate supervises work and needs decisions from the person it works for. docstrap publishes
documentation and gives that person a place to read it and answer the questions it poses. The two meet
today through a bridge written into the firstmate fork: 1,424 lines of bash that export question
documents into project repositories, read answers back out of docstrap's answer store, and close held
decisions without a firstmate turn, plus a task exporter that writes firstmate's backlog into a docstrap
project that lives inside the firstmate home.

That bridge is the wrong shape. Firstmate, docstrap and every other tool on this workstation run under
one harness, Claude Code, and Claude Code documents how a tool offers capabilities to a session (an MCP
server), how a session learns when and how to use them (a skill), and how a tool tells a running session
that something happened (a plugin monitor). This proposal puts the integration on those seams.

docstrap gains an MCP server, run over stdio as a child of the Claude Code session that uses it. The
server lets a session publish into a space docstrap owns, export its open backlog, ask questions, read
the answers, and be told when a person has finished answering. docstrap also ships a skill that says when
a session should ask through docstrap rather than in chat, how to compose what it asks, and what to do
when the answers come back. Firstmate is a session like any other: it loads the skill and calls the
server. Nothing in docstrap depends on firstmate's code, nothing in firstmate's code depends on docstrap,
and the bridge code in the fork is retired once the skill and the server exist.

The same change fixes the question surface. Finding the questions that wait on a person is not a hunt:
open questions are listed first and answered ones after; any answer can be edited; answers are kept apart
from the questions; every question carries its project in its handle and sits under a block naming the
project, its documents and the tasks it gates. Pages a client publishes are cleaned up when the work
they describe closes.

## §2 The Claude Code seams this design stands on

Everything in this section was read from the Claude Code documentation at `code.claude.com/docs/en/` on
2026-10-31. Each fact names the page and section it comes from.

### §2.1 MCP servers over stdio

A stdio server is registered with `claude mcp add [options] <name> -- <command> [args...]`, at one of
three scopes: `local` (the default, stored in `~/.claude.json` under the project's path), `project`
(stored in `.mcp.json` at the project root) or `user` (`~/.claude.json`, every project). Claude Code
starts the server as a subprocess of the session. (`mcp.md`, "Option 3: Add a local stdio server" and
"MCP installation scopes".)

Claude Code sets `CLAUDE_PROJECT_DIR` in the spawned server's environment to the project root, and that
value is stable for the session: it does not change when working directories are added. (`mcp.md`, the
paragraph on `CLAUDE_PROJECT_DIR` under the stdio section.) §4.1 builds client identity on this.

A tool result above 10,000 tokens draws a warning, and the default ceiling is 25,000 tokens, adjustable
with `MAX_MCP_OUTPUT_TOKENS`; a tool can raise its own ceiling with `_meta["anthropic/maxResultSizeChars"]`
in its `tools/list` entry, up to 500,000 characters. (`mcp.md`, "MCP output limits and warnings".)
Server start-up is bounded by `MCP_TIMEOUT`, and a main-conversation call still running after two
minutes becomes a background task. (`mcp.md`, "Time limits on MCP tool calls" and "Automatic
backgrounding of long tool calls".)

Resources are referenced in a prompt as `@server:protocol://path`, and Claude Code gives the model tools
to list and read a server's resources. Resource templates and resource subscriptions are not documented.
A server may send a `list_changed` notification when its tools, prompts or resources change, and an
interactive session refetches the list. (`mcp.md`, "Use MCP resources" and "Dynamic tool updates".)

Streamable HTTP is the documented remote transport and SSE is deprecated (`mcp.md`, "Option 1" and
"Option 2"). This design uses neither: the server runs on the same machine as the session and the person.

### §2.2 Skills

A skill is a directory holding `SKILL.md`: YAML front-matter, then markdown instructions. Its
`description` says what the skill does and when to use it, and is what Claude uses to decide when to
apply it; only descriptions are always in context, and the body loads when the skill is invoked.
`user-invocable: false` keeps a skill out of the person's slash commands while leaving it to the model.
A skill may carry supporting files beside `SKILL.md`, referenced from it. Skills load from
`~/.claude/skills/`, from a project's `.claude/skills/`, and from a plugin's `skills/`. (`skills.md`,
"Frontmatter reference", "Control who invokes a skill", "Add supporting files" and "Choose where skills
load".)

### §2.3 Plugins, and the monitor that carries a notice

A plugin is a directory that bundles skills, MCP servers (`.mcp.json` at the plugin root), hooks and
monitors under one name; `.claude-plugin/plugin.json` is its optional manifest. `${CLAUDE_PLUGIN_ROOT}`
is the installed plugin's directory and `${CLAUDE_PROJECT_DIR}` the session's project root, and both
resolve in MCP server fields and monitor commands. A directory holding `.claude-plugin/marketplace.json`
is a marketplace a person adds once and installs from. (`plugins-reference.md`, "Standard layout",
"mcpServers" and "Environment variables"; `plugins/create-marketplace.md`.)

A monitor is a shell command that runs in the background for the whole session, and what it prints
reaches Claude as notifications. It runs in the session's working directory, starts either at session
start or the first time a named skill runs (`when: "on-skill-invoke:<skill>"`), and does not start in a
non-interactive `-p` session. The manifest key is `experimental.monitors`. (`plugins/components.md`,
"Monitors"; `plugins-reference.md`, "monitors".)

Channels, a separate research-preview feature, let an MCP server push events into a session, but only
when the session was started with `--channels` or, for a server not on Anthropic's allowlist,
`--dangerously-load-development-channels`, which shows a confirmation prompt at every launch.
(`channels.md`, "Research preview"; `channels-reference.md`, "Test during the research preview".) §14
says why this design delivers its notice through a monitor instead.

## §3 What exists today

### §3.1 The bridge in the firstmate fork

Three pieces of the fork are docstrap-specific and absent from upstream firstmate.

`bin/fm-procevent-docstrap.sh` is an adapter for firstmate's process-event runner. Its `export` renders a
question document from a payload firstmate composes, writes it into a project repository, and records
privately which `Q<n>` label asks about which held task. It refuses questions that break the rules a script
can check: not one interrogative sentence, two askable things joined with "and", "A or B" offered instead
of asking about A, or text opening with a question label. It drops context references unless a
configuration flag is set, and keeps one only when the path exists in the project and the held task's own
record names it, emitting it as an `fm-ref:` line. `arm` registers the reader once firstmate's captain-hold
script has bound the source to the keyed-answer intake. `notice` is the command docstrap's
answers-done prompt runs: it reads the project's answer store once, without modifying it, maps labels to
task ids through the private record, and feeds the keyed-answer intake, which closes or releases each held
task with no firstmate turn. Because a `Q<n>` label is a position, any re-export that changes the mapping
re-baselines the read position, and the reader refuses to deliver when the store looks replaced or cut
back. The same `notice`, pressed on firstmate's task page, appends each new task decision to the task's
recommendation history under `data/task-census/` and re-runs the task export.

`bin/fm-task-export.sh` writes every open backlog task, merged with optional census records and
recommendation histories, to `data/docstrap/docs/triage/tasks.json`, which docstrap's task tool reads. It
sets each row's `page` when a task page exists beside it.

The `process-event-sources` skill carries a paragraph on exporting and arming docstrap questions, and
`docs/configuration.md` carries the `config/docstrap-references` flag and the `answers_done_command`
setting firstmate asks docstrap to hold.

Upstream firstmate's own `bin/fm-captain-hold.sh` is not part of the bridge. It owns held decisions and
the one keyed-answer intake, and this design keeps using it as it is.

### §3.2 Firstmate's docstrap project inside its home

Firstmate's review documents, question pages and triage pages live in a docstrap project at
`data/docstrap` inside the firstmate home, registered as a store, its `promdance` entry linked to the
store's `firstmate` directory. The home's own `.docstrap` declares `ignore: true`; this project builds only
because docstrap does not check a directly registered store's ancestors. It holds `docs/proposals`,
`docs/plans`, `docs/research`, `docs/questions` (one hand-maintained open-questions page and a `refs/`
directory of document copies) and `docs/triage` (the task tool page, `tasks.json`, one page per task under
`tasks/`, and dated snapshots under `archive/`).

Nothing removes what stops being current. On 2026-10-31, 28 of 117 task pages described tasks no longer
open and 11 copies in `questions/refs/` were linked by no page; both were removed by hand. The
open-questions page records answers beside the questions it asks, and its question numbers come from a
counter kept in firstmate's agent memory.

### §3.3 What docstrap already has

The answer store (spec §8.1) keys an answer on the metadata document id and the question's label, keeps
drafts beside submitted answers, keeps every superseded answer in `answers-history.md` (spec §8.1.4), and has
one owner, `docstrap.answers`. `docstrap.pairing` is the one place questions and answers are put side by
side (spec §8.2), and `/api/answers` serves that pairing without drafts. The addendum (spec §8.3) stamps
`answered_version`, a digest over what was decided and nothing else. The answers-done prompt (spec §8.10) runs a
configured command once per press, with the project and document.

The `docstrap-questions` directive labels a question by its required `:question-id:`, and an answer to it
is keyed on that id (spec §8.1.1(2)). The task tool (`docs/tasks.md`) renders a task file and records one
decision per task under the label `task/<task-id>`. Plan 0002 put a plugin seam on pluggy and one settings
surface for source folders with roles. Roadmap §4.10 records that docstrap exposes its capabilities over
MCP, built with FastMCP, as a transport over the owners that already exist and never a second copy of
them. `docstrap.firstmate` detects a firstmate home by its shape.

## §4 The client and its space

### §4.1 A client is a Claude Code project directory

A client is whatever Claude Code session calls the server. It is identified by the canonical form of the
`CLAUDE_PROJECT_DIR` Claude Code hands the server (§2.1), resolved through
`projectfinder.canonical_dir` so that a worktree and its main checkout are one directory, the same rule
promdance backups already use. A firstmate home is one client; a secondmate home is another; a worker
session in a project worktree is a third, and sees none of the first two's questions or notices.

A client takes a name once, with `claim_client` (§5.2), and the name becomes the slug of its space's
project on the site. A name another directory holds is refused. Nothing else establishes identity, and
nothing needs to: a stdio server has no network peer, and the directory is a fact the session already has.

### §4.2 The space: what the client adds, and what docstrap writes

Each client has one space under docstrap's own data directory. Its location is docstrap's business; no
tool argument or result names it, and a client never reads or writes it with file tools. It has two parts
with opposite owners.

The source part holds what the client adds through the server and nothing else: pages, task pages, the
backlog, question sets, and reference copies (§9). The server writes these files on the client's behalf
and is the only writer; docstrap's builds and tools never add to it. Docstrap may remove from it, under the
rules of §10 and only those.

The answer part holds what people write through docstrap's tools: the client project's `answers.md`,
`answers-history.md` and addenda. It is the project's declared `draft` source in plan 0002's terms, so
`docstrap.drafts.draft_root` finds it with no promdance involvement, and promdance is turned off for this
project in the `.docstrap` docstrap writes for it.

### §4.3 How the space is built and served

The space is a docstrap project like any other, registered as a store when the client is claimed and
built by the ordinary build. A question set is stored as YAML, the form the client supplied, and composed
into its page during the Sphinx run as docutils nodes, by a source parser registered the way the section
page parser is (spec §7.8.2). No markdown is produced at any point. Each question in the composed page is a
`docstrap-questions` block whose `:question-id:` is the question's handle (§8), so its answers are keyed on
the handle and survive any reordering of the set.

`docstrap.questions` gains a second reader for this source format: the questions a set declares, under the
labels it declares. That keeps the module the one owner of "what questions does this document pose", and
pairing, the answers API, the `answered` tool and the question panels work on a question set unchanged.

Every page in the space is readable with no tool present: the composed question page shows its context
blocks, handles, questions, options and reference links as plain HTML.

## §5 The MCP server

### §5.1 Shape

`docstrap mcp` runs the server over stdio, built with the FastMCP class of the official MCP Python SDK, as
roadmap §4.10 decided. The SDK is a new dependency, added with `uv add` in the stage that needs it, and
the captain is told before it is added. The server is registered by the plugin of §6, so a session that has
the plugin enabled has the server.

The server is a transport. Each tool calls the module that already owns what it touches: `docstrap.answers`
for answers, `docstrap.pairing` for the question-answer view, `docstrap.metadata` for document identity,
`docstrap.projectscope` for resolving a project, and the task tool's reader for the task file. Two new
modules own what is new: `docstrap.clients` owns client identity and the space (§4), and
`docstrap.notices` owns the notice log (§5.4). Nothing the server does is possible only through the server;
each operation is also a `docstrap client` subcommand, which is how the skill hands over data that should
not pass through the model (§5.2(3)).

### §5.2 Tools

Every tool acts for the calling client and sees only that client's space, plus the registered projects it
references.

1. **`claim_client(name)`** binds the calling directory to a name and creates the space and its project.
   Calling it again with the same name is a no-op.
2. **`client_status()`** is the reconciliation call. It returns everything the client has published (each
   item's id, kind, title, the tasks it serves and its viewable locator), the time of the last backlog
   export, every item archived since the last status call, the highest question serial the client has
   published (§8), and every question set whose answers have changed since the client last read them,
   judged by the set's `answered_version` (§3.3). A session calls it at start and after any gap, and needs
   nothing else to catch up.
3. **`put_backlog(path)`** replaces the client's open backlog with the task file at `path`, a file the
   client wrote and hands over, in the task-file contract `docs/tasks.md` §2 describes, which this proposal
   moves into docstrap as a Pydantic model owned by `tools/tasks/spec.py`. The file is read by path rather
   than passed as an argument because a backlog of over a hundred tasks should not travel through the
   model. A row's `page` is no longer the client's to supply: docstrap knows which task pages it holds.
   `put_backlog` then applies §10's closing rule and returns the counts, the archived items and the task
   page's locator.
4. **`publish_task_page(task_id, content)`** creates or replaces the markdown page for one task. It is
   refused for a task id absent from the current backlog.
5. **`publish_page(page_id, title, content, tasks, section)`** creates or replaces any other page, such as a
   proposal, a report or a research note, in a section the client names. `tasks` is the list of task ids
   the page serves, and may be empty.
6. **`publish_questions(set_id, title, contexts)`** creates or replaces a question set. Its shape and its
   checks are §7.5 and §8. It returns the set's locator and the handles it accepted.
7. **`retire(id)`** withdraws one item the client published. It is idempotent.
8. **`read_answers(target)`** returns the submitted answers for one question set, one task page (its task
   decisions), or one watched document (item 9): for each question, its handle or label, the question text,
   the current answer as written, when it was submitted, by whom when named, how many earlier answers it
   superseded, and whether it changed since this client's last read. It never returns a draft. It records
   the set's current `answered_version` as read, which is what `client_status` compares against.
9. **`watch_document(project, path)`** and **`unwatch_document(project, path)`** register the client's
   interest in an ordinary document in a registered project, such as a proposal the client wrote into a
   repository, so the answers-done prompt on that document notifies this client and `read_answers` can
   read it.
10. **`export_answers(target, format)`** writes the target's submitted answers, with their questions, to a
    file in `xlsx`, `json` or `yaml` and returns its path (§7.6).

### §5.3 Resources

Two fixed resources per client, for a person or a session that wants to attach them with an `@` mention:
`docstrap://questions/open`, every open question the client has published, grouped by context block; and
`docstrap://answers/unread`, every submitted answer the client has not yet read. They are views over the
same calls as `client_status` and `read_answers`, and reading a resource marks nothing as read. No
resource templates are used, since Claude Code does not document them.

### §5.4 The answers-done notice

A person finishing a document's questions presses the answers-done prompt (spec §8.10), once per document.
This proposal changes what the press does. It appends one notice to the notice log: the client that
published the question set or watches the document, the set or document, the project, and the time. The
log is a file per client in docstrap's data directory, appended to only by the press and read only by
`docstrap.notices`. The prompt is now offered on a document that a client published or watches, as well as
wherever `answers_done_command` is set; that setting stays as a general hook for any other consumer, and
firstmate stops setting it.

The notice reaches a running session through the plugin's monitor, `docstrap notices follow --client
"${CLAUDE_PROJECT_DIR}"`, declared to start the first time the skill of §6 runs. It prints one line per
new notice, naming the client, the set or document, the project and the time, and Claude receives each
line as a notification. A worker session in another directory follows another client's log, which is
empty, so it hears nothing.

The notice is a wake-up and carries no answers. What decides whether there is anything to read is
`client_status`'s comparison of `answered_version`, so a notice printed while no session was running, or
missed for any other reason, is caught by the next `client_status` call. Nothing reads the answer store on
a timer.

### §5.5 Limits

Every tool's result is kept under the 10,000-token warning threshold of §2.1 by construction: lists return
identifiers, titles and locators, and full text comes from per-item calls. `read_answers` on a large set
pages its result, and no tool raises its own ceiling. Every tool finishes in well under the two minutes
after which Claude Code backgrounds a call.

## §6 The skill

docstrap ships a Claude Code plugin from inside its package: the MCP server in the plugin's `.mcp.json`
(`docstrap mcp`), the monitor of §5.4, and a skill, `docstrap-questions`. The plugin directory is also a
one-plugin marketplace, so a person installs it once with `/plugin marketplace add` and `/plugin install`.
The two skills `docstrap init` already installs (spec §9) are untouched.

The skill's description says to load it when a session is about to ask a person for decisions, when a
docstrap notice arrives, at the start of a session whose project is a docstrap client, and when a backlog
or task page should be published. Its body owns the following, in prose a session follows.

When to ask through docstrap. A decision waiting on a person goes into a question set rather than chat
when it needs its documents beside it or when there are several. Before asking, the session reconciles:
it drops a question a recorded answer already decides, and never asks a settled question again.

How to compose a question set. Questions are grouped into context blocks, usually one per project (§7.5).
Each question is one interrogative sentence asking about one thing, with numbered options when there are
options, never implying the options are exhaustive, and is ordered so that the answer most likely to make
later questions moot comes first. Each question carries a handle (§8). A reference is included only when
the gating task's own record names it (§9). The session never writes a person's answer into a context
block, a question, or any page it publishes.

How to publish the backlog and task pages. When its backlog changes, the session writes the task file
and calls `put_backlog` with its path; when it analyses a task, it publishes that task's page.

What to do on a notice. On a notice line, or when `client_status` reports changed answers, the session
calls `read_answers`, reads what the person wrote, and decides what each answer means. Only then does it
record anything, through its own decision path (§7.4). It retires a set whose questions are all settled.

A firstmate section. When the session's project is a firstmate home, which the skill tells by the shape
`docstrap.firstmate` already uses, the decision path is firstmate's own: a question's handle is written on
the held task it gates when the set is published, and after reading an answer firstmate records it with
`bin/fm-captain-hold.sh answer <task-id> --decision-file <file>`, closing or releasing the task itself. The
backlog file is written by firstmate's own backlog export (§11(9)). These are upstream firstmate commands;
the skill names them and adds no code to firstmate.

## §7 The question surface

These rules hold for every question docstrap shows, in the question panels (spec §7.6), in the viewer's
question drawer (spec §7.10), and on a client's question pages.

### §7.1 Open means unanswered, and open comes first

A question is open exactly when it has no submitted answer; a draft does not make it answered, which is
spec §8.1.3's rule. The question list shows two groups: every open question first, then every answered
question. Within each group, a client's questions stay under their context blocks and a document's stay in
document order. The header counts both groups. A person looking for what waits on them reads the first
group and stops.

A composed question page orders its questions as the client published them, because the page is built
before answers exist and answers are resolved at serve time (spec §7.7). With the tools present, the page moves
answered questions into an answered group below the open ones in each context block. With no tool present,
the page is the client's order, unmarked, as spec §7.7 already accepts.

### §7.2 Every answer can be edited

Selecting an answered question opens its answer in the editor, and typing revises it: the revision is a
draft beside the standing answer until the person finishes, then it supersedes it, and the earlier answer
goes to history (spec §8.1.4). There is no revise control and nothing to explain. This is already how the store
behaves; the rule makes the list offer it, by putting answered questions in reach rather than hiding them.

### §7.3 Answers are kept apart from questions

An answer is never written into the source of a question. A question set's YAML has no answer field, and
`publish_questions` refuses one. A client never composes a person's words into context text, which is the
practice that put answers inside firstmate's question pages. On screen, an answer appears only in the
answer editor and in the answer block the `answered` tool draws beneath a question, distinct from the
question and its context.

### §7.4 A record of an answer is made afterwards

The answer store holds what the person wrote, and nothing else records it at the moment of answering.
Whatever record a client keeps of a decision is made after the client has read the answer and analysed
what it means, and is the client's own: for firstmate, the captain-hold decision record of §6. No answer
closes, releases or changes any task by itself.

### §7.5 Every question sits under a context block

A question set is a title and a list of context blocks. A context block names the project (its
registered docstrap slug when it has one, otherwise the client's name for it), the documents the
questions concern, as references (§9), the tasks the questions gate, each by id and title and linked to
its task page when the client has one, and a short paragraph of context. Under it sit its questions. A set
may hold several context blocks for several projects; what `publish_questions` refuses is a question with
no context block above it, a context block with no project, and a question gating no task when the client
has a backlog.

Because the space is docstrap's own, a question can be asked about a project that is not a docstrap
project: its context block names the project and carries reference copies of the documents (§9).

### §7.6 Data leaves as xlsx, JSON or YAML

Answers and questions leave docstrap in one of three formats: `xlsx` for a person, `json` or `yaml` for a
program. Never CSV. `export_answers` writes them (§5.2(10)), the question panels offer the same three as a
download, and the columns or keys are handle or label, project, document, question, answer, submitted, and
superseded count. The `xlsx` writer needs `openpyxl`, a new dependency added with `uv add` in the stage that
needs it, and the captain is told first.

### §7.7 Later: the review-and-revise grid

A later version adds a grid for reframing and revising answers, one row per question, with three columns:
the question; its answer history, which shows only finalized, submitted answers, newest first, read from
`answers.md` and `answers-history.md`; and a new answer, in the multiline autosaving editor the panels
already have. It writes through `docstrap.answers` like every other surface. It is a stage of its own (§13)
and changes none of the rules above.

## §8 Question handles

A question a client asks a person carries a handle: `Q`, a decimal serial, a hyphen, and the short name of
the project it concerns, such as `Q371-docstrap`. The serial is the client's home-wide series, issued once
and never issued again for another question, so a handle always means the question it was first given to.
The project name is lower-case, chosen once per project and never reassigned; for a docstrap project it is
the last segment of its slug unless that collides with another project's name.

The client mints handles, in chat and in question sets alike, from one series. docstrap does not mint
them. It checks three things at `publish_questions`: the shape; that no handle in the set is live in
another of the client's open sets, so one question is asked in one place; and that no serial is reused for
a different project name. `client_status` reports the highest serial the client has published, so a client
that lost its own counter never issues a serial lower than one already out.

On a question page and in the panels, the handle is the question's label, because it is the
`:question-id:` of its block (§4.3). Ordinary documents keep their own `Q1`, `Q2` labels and the finder's
rules for them (`finding-questions.md`); the panels show their project and document in the context header,
so those questions also carry their project wherever they are shown.

## §9 References

A reference in a context block takes one of two forms.

A reference to a document in a registered project is `{project, path}`: the project slug and the path below
its `docs_root`. `publish_questions` resolves it when the set is published. It refuses a project that is not
registered and a path the project does not declare, so a reference is never born broken, and it registers
the document in the metadata store and stores the document id with the reference. The page links the
document through that id, resolved at build to the document's current path, so a rename that docstrap
recorded does not break the link. No copy is made. This is the format
`docstrap-resolve-file-references-h72` consumes when it opens a reference in the reference pane.

A reference to a file outside every registered project, such as a report in the client's own working
files, is `{title, content}`: the client supplies the text, because docstrap reads nothing outside its own
space and the registered projects. docstrap stores it as a reference copy in the client's space, named by
the digest of its content, so two pages citing the same text share one copy.

Whether the client's reference is relevant is the client's judgement, and the skill keeps the provenance
rule the fork enforced in code: a reference is included only when the gating task's record names it.

## §10 Clean-up

A published item lives as long as the work it serves.

A task page lives while its task is in the client's backlog. When `put_backlog` replaces the backlog,
every task page whose task id is absent is archived: moved into the client space's `archive/`, which
docstrap's default `exclude_dirs` keeps out of the site, with the move recorded in the metadata store so
answers keyed on the page keep their document. A page published with `publish_page` or a question set is
archived the same way when every task it serves is absent from the backlog. A page or set serving no task
lives until the client retires it. `retire` archives too. Archiving is reported to the client in the
`put_backlog` result and in the next `client_status`, and is the only removal docstrap performs on its own.

A reference copy lives only while a live page or set links it. After any publish, retire or archive,
docstrap computes the copies the live items link and deletes the rest. The computation reads the client's
sources each time and keeps no index, the rule `fileindex` and section pages already follow.

The dated triage snapshots firstmate keeps today are pages like any other: published with the tasks they
served, archived when those close.

## §11 What the fork code does today, and where each piece goes

1. **`export`** (render a question document into a project repository, record the label-to-task map)
   becomes `publish_questions` into the client's own space. The map is no longer needed: a handle is the
   question's identity, and the gating task is named on the held task by firstmate (§6).
2. **The question rules a script can check** move into `publish_questions`'s validation, unchanged: one
   interrogative sentence, no "and" joining two askable things, no "A or B", no text opening with a
   question label.
3. **`bind` and `arm`**, which connected a source to firstmate's keyed-answer intake and its process-event
   runner, are retired with nothing in their place. No answer closes a task by itself (§7.4).
4. **`notice`** becomes the press's notice log, the plugin monitor and `read_answers` (§5.4).
5. **`source`, `classify`, `terminal`, `answers`, `autohandle` and `read`**, the non-destructive read with
   its durable read position, delivery ledger, re-baselining on renumbering and continuity checks, become
   `read_answers` and `client_status`'s `answered_version` comparison. Re-baselining has nothing left to
   guard: answers are keyed on handles, which do not renumber.
6. **`retire`** becomes `retire`.
7. **Task decisions**, appended by `notice` into firstmate's recommendation histories, become
   `read_answers` on the task page. docstrap shows the newer of firstmate's latest recommendation and the
   captain's decision as the task's latest recommendation at build; nothing writes into firstmate's files.
8. **Context references and `config/docstrap-references`** become the structured references of §9, always
   on and verified at publish. The flag is retired.
9. **`fm-task-export.sh`** keeps the part that is not docstrap's: writing firstmate's open backlog, with
   its census fields, as JSON. It loses its default output path inside the home and its `page` field, and
   becomes a general backlog export that the fork carries as an upstream candidate. Its output is what the
   skill hands to `put_backlog`.
10. **The `process-event-sources` paragraph** on docstrap is removed; the docstrap skill replaces it.
11. **The `docs/configuration.md` sections** on docstrap question references and on firstmate's
    `answers_done_command` value are removed.
12. **The private records** under `state/docstrap-questions` and `state/docstrap-answers` are retired once
    the migration has drained them (§12).
13. **The `data/docstrap` project** is deregistered with `docstrap stores remove` once its content is
    republished; its files stay where they are, as firstmate's own, for firstmate to keep or delete.

## §12 Migration from the fork bridge

Migration moves firstmate's presence into its client space without losing an answer and without moving
any answer between stores, because `docstrap.answers` is the one owner of each store and an answer copied
by anyone else would be an answer the person never gave there.

First, firstmate claims its client and republishes: its backlog through `put_backlog`, each current task
page through `publish_task_page`, and its proposals, plans and research notes through `publish_page`. Pages
for tasks no longer open are not republished.

Second, every armed fork source is drained: firstmate reads each source's store one final time through the
existing `notice` path, so every answer already given reaches its task. Then each open question on the
old pages, including the hand-maintained open-questions page, is asked again in a question set, under its
existing handle with its project name added, and only questions still open are asked. Answers already in
`~/.local/share/promdance/firstmate/answers.md` stay there unchanged as history.

Third, the fork sources are retired with the adapter's own `retire`, firstmate's `answers_done_command`
value is removed from docstrap's user config, and `data/docstrap` is deregistered. The one window this
leaves is an answer given on an old page after its final read; the old pages are deregistered in the same
step, so the window is the time between that read and the deregistration, and the migration reports it
rather than claiming there is none.

Fourth, the fork code of §11 is removed in one change on the fork, leaving the general backlog export as the
only piece that remains, as an upstream candidate.

## §13 Stages

Each stage leaves docstrap's suite green and the live installation building, and each is usable on its
own.

1. **The client space and its pages.** `docstrap.clients`, the space and its project, `claim_client`,
   `client_status`, `put_backlog`, `publish_task_page`, `publish_page`, `retire`, the clean-up rules of §10,
   the `docstrap client` subcommands, and the MCP server carrying those tools. Firstmate migrates its pages
   and backlog (§12, first step) and stops writing into `data/docstrap`.
2. **Questions and answers.** The question-set source format and its composer, the second reader in
   `docstrap.questions`, handles, references, `publish_questions`, `read_answers`, `watch_document`, the
   notice log, the plugin with its monitor and the `docstrap-questions` skill, and the question-surface
   rules of §7.1 to §7.5 in the panels and the drawer. Firstmate drains and re-asks (§12, second and third
   steps).
3. **The fork retired.** The fork change of §12's fourth step.
4. **Data out.** `export_answers` and the panels' download in the three formats of §7.6.
5. **The review-and-revise grid** of §7.7.

Each stage corrects the spec where the code changes it: §0.2 (an MCP server is in scope, as roadmap §4.10
already says), §7.6 (the list's two groups), §8.10 (the press now records a notice) and §9 (the plugin and
its skill), keeping every section number. Roadmap §4.10 moves to the implementation record as stages land.

## §14 Architecture and tradeoffs

The server is docstrap's because everything it touches is docstrap's: the space, the answer store, the
metadata store and the site. Firstmate keeps what is firstmate's: its backlog, its held decisions and the
authority to settle them. The skill is the only place the two are described together, and it is
instructions, not code, so neither side carries the other's logic.

Stdio means the server is a child of the session that uses it and lives exactly as long as that session.
It has no port, no network peer and no authentication to get wrong, and the session's own project
directory identifies it. The cost is that the server cannot be reached by anything except its session,
which is why the notice is a file the browser-side press appends to and a monitor the session runs, rather
than something the server pushes.

The notice uses a plugin monitor rather than a channel. A channel would let the server push into the
session directly, but during the research preview a server of docstrap's kind registers as a channel only
in a session started with `--dangerously-load-development-channels`, which asks for confirmation at every
launch and is ignored in non-interactive sessions (§2.3). A monitor needs no launch flag. It shares the
limit of not starting in `-p` sessions, and its manifest key is marked experimental, so a monitor that does
not start is expected: `client_status` at session start is what makes a missed notice cost a delay rather
than a lost answer.

Removing automatic closing costs one firstmate turn per batch of answers, where the fork closed held
decisions with none. That turn is where the answer is read and its meaning decided, which is what §7.4
requires, and it removes the whole class of failures the fork's re-baselining and continuity checks
existed to contain.

Moving firstmate's pages into docstrap's space ends docstrap building a project inside a home that
declares `ignore: true`, and ends firstmate writing question documents into project repositories. The cost
is that a question is no longer a file in the project it concerns; the context block's references and the
panels' reference pane are what put it beside its documents.

Two new dependencies arrive: the MCP Python SDK in stage 1 and `openpyxl` in stage 4.

## §15 The folded records and their questions

Five firstmate records were folded into this proposal on 2026-10-31. Each question they held is answered
by a ruling, made moot by one, or settled by this design and so answered by the decision on this proposal.
Two remain, and §16 restates them in full.

### §15.1 A firstmate skill that exports held questions per project

The record asked for a skill that gathers held questions per project and puts them beside that project's
documentation, owning which questions are worth asking and in what order, grouping by project, and
reconciling before asking; it noted that only docstrap projects could be reached, and that a question
document could not be named `index.md`. The skill of §6 is that skill, shipped by docstrap. Grouping
becomes context blocks (§7.5), reconciliation is in the skill (§6), and a non-docstrap project is reachable
through reference copies in the client's space (§7.5, §9). The `index.md` constraint does not arise,
because a question set is composed from YAML into a page docstrap names.

### §15.2 Four calls on firstmate's presence in docstrap

1. Whether firstmate's docstrap project should live outside the firstmate home: answered by the ruling that
   the integration is a docstrap-owned server. Firstmate's pages move into docstrap's own space (§4.2), and
   docstrap does nothing inside the home.
2. Whether the owning bridge should be firstmate's adapter or a `ds_bridge_fm` package beside docstrap:
   moot. The ruling replaces both with the server and the skill.
3. Whether answers to a proposal's own numbered questions should return as revision input without closing
   a held decision: answered by the ruling that any record of an answer is made afterwards from analysis.
   No answer closes anything (§7.4), and `watch_document` is how a client reads a proposal's answers (§5.2(9)).
4. Whether the viewer's proposal actions should reach firstmate's documents only through the bridge:
   answered by the decided rule that only the client adds to its space. Viewer actions that move or create
   documents do not act on a client's space; the client publishes and retires its own items.

### §15.3 Firstmate gets its project contexts from docstrap

The idea that firstmate should take its project contexts from docstrap is met by references (§9): a
context block names registered docstrap projects and their documents, resolved by docstrap at publish.
Nothing further is designed here.

### §15.4 The MCP publication channel spec

1. Retention default: answered by the ruling that a task's page goes when its task closes, extended in §10
   to every item that serves tasks; an item serving none lives until retired. No time-based retention.
2. Whether docstrap notifies a client when it drops a publication: settled by this design. Docstrap drops
   only what the client's own backlog export implies, and reports it in the result of that call and in
   `client_status` (§10).
3. Whether this work carries the three-panel answering surface: answered by the question-surface rulings,
   which are part of this proposal (§7).
4. What establishes client identity, and whether a client has one source area: settled by this design
   under the stdio ruling. Identity is the session's project directory, and a client has one space (§4).
5. Whether to use firstmate's fleet activity ledger: moot. The backlog arrives through `put_backlog` (§5.2(3)).
6. Which capability to specify first, publication, inbound answers or repository observation: answered by
   the ruling, which names publication and answers. Repository observation is not part of this proposal.
7. Whether a document should be identified by commit and path for repository observation: open, restated
   as §16 Q1.
8. Whether docstrap should render diffs between a worktree copy, the project's main folder and the
   committed head: open, restated as §16 Q2.
9. Whether the composed-answers path needs firstmate-side code: answered by the ruling. It needs none;
   `read_answers` is the composed view and firstmate's existing commands record the decision.
10. Whether a firstmate process-event extension is worth building: moot. The ruling retires the bridge,
    and nothing replaces it inside firstmate.

### §15.5 Five calls on question identifiers

1. Whether a handle should be a two-letter project code and a serial, such as `DK12`: answered by the
   ruling that every question carries its project after its number, as in `Q371-docstrap` (§8).
2. Whether a handle is never issued again for another question: settled by the practice firstmate already
   keeps, numbers never reused.
3. Whether the long form should add a mnemonic facet slug: answered by the same ruling, whose facet is the
   project. There is one form, `Q<serial>-<project>`.
4. Whether documents keep docstrap's `Q<n>` labels with the handle beside each: settled by this design
   under the ruling. A client's question pages label each question by its handle, through the directive's
   `:question-id:`; ordinary documents keep their own labels (§8).
5. Whether handles replace per-message numbering in chat: settled by the practice firstmate already keeps,
   one series used in chat.

## §16 Open questions

These come from the MCP publication channel spec, where they were recorded for repository observation.
Neither gates any stage of this proposal.

Context for Q1: identifying a document by its commit id and file path would let docstrap work with a
repository that has no checkout and would make a diff addressable; it is open whether every docstrap
surface could carry that identity or only the surfaces reached through the repository hook.

**Q1.** For repository observation, should a document be identified by its commit id and file path?

Context for Q2: an uncommitted worktree copy may not be reachable at all under the rule that docstrap
touches nothing in a working copy, and the alternative to one view is three pairwise views.

**Q2.** For repository observation, should docstrap render the differences between a worker's worktree copy
of a document, the project's main working folder and the committed head as one three-way view?

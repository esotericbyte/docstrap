# docstrap

A user-scoped documentation publishing tool. Docstrap finds documentation
projects by the `.docstrap` file at their root, builds each one with Sphinx
(MyST markdown, Sphinx, MkDocs and Quarto layouts), and publishes them together
as one site with a document viewer, search, and on-page tools for answering the
open questions a document poses.

A build reads a project and never writes into one: everything it composes lives
in the build's own output directory.

## Install

Docstrap needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```
uv tool install git+https://github.com/esotericbyte/docstrap
docstrap init
```

`docstrap init` creates docstrap's user-level directories and databases, and
offers to install its Claude Code skills.

To work on docstrap itself:

```
uv sync
uv run pytest
```

The on-page tools and the viewer are Svelte, and their built bundles are
committed, so using docstrap needs no Node. Changing anything under a `ui/`
directory does: run `npm ci` once, then `npm run build`, and commit the changed
files under `static/`. `npm ci` is also needed before `uv run pytest`, because
part of the suite runs the TypeScript tests under Node.

## Usage

Register a project, build it, and serve the site:

```
docstrap register --path ~/src/my-project --title "My Project" --docs-root docs
docstrap build --config ~/src/my-project/.docstrap --out ~/my-project-site
docstrap serve --site ~/my-project-site
```

`docstrap questions ~/src/my-project` lists the questions the project's
documents pose, found by their `Q1.`, `Q2.` labels. `docstrap --help` lists
every command.

## Licence

MIT. See `LICENSE`.

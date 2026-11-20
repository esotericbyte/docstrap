# Next steps: plans for docstrap v0.1

**Date:** 2026-11-04
**Status:** captured; the headings of a plan not yet written. Source: the captain's direction of 2026-11-04, kept verbatim in this package's promdance note `2026-11-04-viewer-navigation-tabs-and-tools.md`.

Docstrap is at 0.0.3. The viewer reached its current shape by fixing what hurt; the next version is planned first. This note names what the plan must settle, in the order the pieces depend on each other.

## 1 The model

Document navigation on the left, the document in the centre, tools on the right. Navigation reaches precise locations (a heading, a numbered requirement), follows Sphinx cross-references, and switches between related versions of one document, such as a specification's direct version and its version with provenance.

## 2 The left drawer

Two parts. Above, the document tree, to change the selected document. Below, the table of contents of the selected document, which today is missing altogether where there used to be several. Where the TOC is built is a plan decision: by Sphinx in the theme and carried into the page as HTML or JSON, or by the viewer from the document content. On small layouts the tree gives way to a breadcrumb at the top of the pane: entering a document (double click or Enter) adds it to the breadcrumb, and a navigate-out control on the left brings the tree back.

## 3 The right drawer

Closed and opened by a narrow tab control. It holds tools, of which the question tool is one; a tool opens when a document that uses it is selected, the question tool when the document poses questions.

## 4 Multi-tab viewing

More than one document open at once, so related documents can be browsed while answering questions. In that mode the right drawer has independent tabs, so a set of questions or another tool operation stays put while the centre switches between documents.

## 5 The question tool

The pin mechanic is revamped. Editing, revising and submitting answers is organised better than today (one submission for the page rather than a button per answer is the first step already asked for).

## 6 Firstmate context

What firstmate exports to docstrap keeps its references to the projects and the tasks each item relates to.

## 7 Editorial review tools

Added 2026-11-04, same source. Professional editorial tools to mark up a document: mark ranges of text as good or problematic, and attach comments of a few kinds, such as "needs refinement" and "overly constrained", so a specification can be reviewed in place and the marks read back by whoever revises it.

What exists today, for the plan to build on or retire: the `review` tool (`tools/review`), which walks the rendered page, puts a tri-state mark on each sentence and heading, and submits the marks to a file whose path is copied to the clipboard; it is declared off by default and shown through the launcher. The annotations store (`annotations.py`), a W3C Web Annotation store with the protocol subset Annotorious needs, is built on the server side and has never been exercised by a client; the 2026-10-10 note `2026-10-10-annotorious-tool.md` sketches the client as a tool. Neither carries typed comments; the review tool carries no comment at all.

## 8 Open decisions for the plan

Q1. Is the table of contents built by Sphinx in the theme and prepended to the page, or built by the viewer from the rendered document?

Q2. On wide layouts, do the tree and the breadcrumb both exist, or is the breadcrumb the small-layout form only?

Q3. Does a tab in the right drawer bind to one document, or stay independent of which document is in the centre?

## 9 Firstmate's area, question documents and the reference system

Added 2026-11-04, later the same day, verbatim:

> that page you linked is nearly empty. if there are no answers attached and it isn't a report that is renewed the firstmate area of docstrap needs to be swept up. Firsmate docstrap should have two different types of quetion docs. one by project/task and another for summaries and both firstmate and the next version of docstrap need to create a reference system between tasks, repositories, projects  and tasks , documents sections, and documents serving different fuctions. like consise complete statement of requirements , versus deliberation. Also need a mechanic that pushes against absoutes and overly constrained features that add alot of complexity, and encorage good object oriented designs structured around desgin patterns and that take advantage of polymorphic objects and feature injection.

What this adds to the plan: two kinds of question document in firstmate's area (per project or task, and summaries); a reference system linking tasks, repositories, projects, document sections and document functions (a concise complete statement of requirements against a deliberation), shared by firstmate's export and docstrap's viewer; and a review mechanic that pushes back on absolutes and over-constrained features and favours designs built on patterns, polymorphic objects and feature injection, which belongs with the editorial tools of §7.

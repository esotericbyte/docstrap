"""Docstrap's Sphinx adapter.

This package is the renderer side of the tool architecture, not the
tools themselves. The tools live in :mod:`docstrap.tools`, one
directory each, and each declares its own Sphinx entry point.

* :mod:`docstrap.sphinx.tool_support` — the extension points a tool
  attaches to on the Sphinx side: asset registration named from the
  declaration, page metadata injection, and the page context the
  launcher decides with.
* :mod:`docstrap.sphinx.launcher` — the single visibility control's
  extension. Not a tool; it is what tools declare themselves to.

Nothing here names a tool. The generated ``conf.py`` gets its
``extensions`` list from
:func:`docstrap.tools.registry.sphinx_extensions`, which reads the
declarations, so a new tool directory reaches the built site without
this package or the layout template being edited.
"""

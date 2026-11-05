"""The viewer shell — one Svelte application over a built site.

Three regions on
one page: a navigator listing every project and document the build
published, the selected document's published page in a frame, and the
qapanels instrument's three panels in a drawer whose state does not
follow the frame.

It is NOT a tool. A :class:`~docstrap.tools.declaration.ToolDeclaration`
means per-page assets and a Sphinx extension, and the shell has neither:
declaring it would put Skeleton and Tailwind on every documentation page,
which is the per-page cost an instrument is meant to avoid and the
collision with the host theme's styling a tool must not cause. It
is a page of its own, copied into the site root by the build beside the
manifest that tells it what the site contains.

``ui/`` is the Svelte source and ``static/`` the committed build of it,
written by ``build-tools.mjs`` exactly as a tool's bundles are, so
installing docstrap still needs Python only.
"""

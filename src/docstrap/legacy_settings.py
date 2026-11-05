"""The settings shape docstrap read before the ``plugins`` block, frozen.

Before the ``plugins`` block, one plugin's switch was a docstrap key of its own: a
tri-state boolean at the top of a ``.docstrap``, on each of its entries,
and in the user config, which also carried a second key for that plugin's
projects root. An installation that has not run ``docstrap config
migrate`` still says it that way, and :mod:`docstrap.config` and
:mod:`docstrap.settings` read it, or refuse it, through the names below.

This is the one module in docstrap that spells those old keys, and it
spells nothing else. Like the frozen recogniser in
:mod:`docstrap.generated_indexes` it describes the past and changes with
nothing: a recogniser of an old shape has to keep describing that shape,
whichever plugin the key belonged to and wherever that plugin now lives.
"""
from __future__ import annotations

#: The plugin the old keys belonged to, and its name in ``plugins:``.
PLUGIN = "promdance"

#: The old tri-state key, at every level. It became
#: ``plugins.<PLUGIN>.enabled``.
ENABLED_FIELD = "promdance"

#: The old user-config key for the plugin's projects root, and the key of
#: the plugin's block it became.
PROJECTS_ROOT_FIELD = "promdance_projects_root"
PROJECTS_ROOT_KEY = "projects_root"

#: Both old user-config keys.
USER_FIELDS = (ENABLED_FIELD, PROJECTS_ROOT_FIELD)

#: The plugin's member rule as migrate writes it: what was built in before
#: it was a setting.
MEMBERS_KEY = "members"
MEMBERS = ("apps/*", "packages/*")

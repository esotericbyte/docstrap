"""The one settings surface: sources with roles and mounts, and plugins.

Four things are held here:

1. **Compatibility.** An installation that has not run `docstrap config
   migrate` reads exactly as before: the `docs` default, the old
   `promdance:` keys where they stand, promdance on when nothing says.
   A user config that never mentions the new shape is such an
   installation, and so is a machine with no user config at all.
2. **Precedence.** Installation < repository < project, and a `sources`
   list wins whole — lists are never merged. A plugin's `enabled` is
   tri-state; its other keys merge key by key.
3. **Round-trip fidelity.** `docstrap.settings` writes both files without
   losing a person's comments, key order or indentation.
4. **Migration.** A dry run by default that writes nothing; `--apply`
   writes; the result reads as the same effective settings; a second run
   changes nothing; afterwards an old-shape key is a load error.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from docstrap import fileindex, paths, projectscope, sectionindex, settings, user_config
from docstrap.cli import app as docstrap_app
from docstrap.config import DocstrapConfigError, Source, load
from docstrap.layouts import markdown
from docstrap.legacy_settings import PLUGIN
from docstrap.scan import scan

runner = CliRunner()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _user_config(text: str) -> Path:
    return _write(paths.user_config_file(), text)


def _projects(root: Path, docstrap: str) -> list:
    config = _write(root / ".docstrap", docstrap)
    return list(scan(load(config)))


def _setting(project):
    """The old switch's plugin setting for ``project``, as a build resolves it."""
    return settings.plugin_setting(
        PLUGIN, project.project_plugins, project.repository_plugins, settings.installation()
    )


def _installation_stated() -> bool | None:
    return settings.stated_enabled(settings.installation().plugins, PLUGIN)


def _projects_root() -> str | None:
    """The plugin's ``projects_root`` key at installation level, unread by docstrap."""
    return (settings.installation().plugin_block(PLUGIN) or {}).get("projects_root")


def _only(root: Path, docstrap: str):
    projects = [p for p in _projects(root, docstrap) if p.kind == "project"]
    assert len(projects) == 1
    return projects[0]


# --- 1. compatibility: an unmigrated installation reads as it always did ------


def test_with_no_user_config_a_project_reads_the_docs_default(
    tmp_path: Path, user_dirs: Path
):
    """No user config is an unmigrated installation, not an empty one."""
    assert not paths.user_config_file().exists()
    project = _only(tmp_path / "repo", "version: 1\ntitle: p\n")
    assert project.docs_dir == (tmp_path / "repo" / "docs").resolve()
    assert [(s.role, s.mount) for s in project.sources] == [("documentation", "")]
    assert _setting(project).enabled is True
    assert _setting(project).level == settings.DEFAULT


def test_an_unmigrated_user_config_keeps_the_old_keys_and_the_docs_default(
    tmp_path: Path, user_dirs: Path
):
    _user_config(
        "version: 1\nstores: []\npromdance: false\n"
        f"promdance_projects_root: {tmp_path}\n"
    )
    project = _only(tmp_path / "repo", "version: 1\ntitle: p\n")
    assert project.docs_dir == (tmp_path / "repo" / "docs").resolve()
    assert _installation_stated() is False
    assert _setting(project).level == settings.INSTALLATION
    assert _projects_root() == str(tmp_path)


def test_an_unmigrated_docstrap_keeps_its_promdance_keys(
    tmp_path: Path, user_dirs: Path
):
    projects = _projects(
        tmp_path / "repo",
        "version: 1\ntitle: r\npromdance: false\nprojects:\n"
        "  - path: a\n    promdance: true\n  - path: b\n",
    )
    a, b = projects
    assert (settings.stated_enabled(a.project_plugins, PLUGIN),
            settings.stated_enabled(a.repository_plugins, PLUGIN)) == (True, False)
    assert _setting(a).level == settings.PROJECT and _setting(a).enabled
    assert _setting(b).level == settings.REPOSITORY and not _setting(b).enabled


def test_one_file_may_not_state_both_shapes(tmp_path: Path, user_dirs: Path):
    config = _write(
        tmp_path / ".docstrap",
        "version: 1\npromdance: true\nplugins:\n  promdance: {enabled: false}\n",
    )
    with pytest.raises(DocstrapConfigError, match="config migrate"):
        load(config)


# --- 2. precedence -------------------------------------------------------------


MIGRATED = "version: 1\nstores: []\nplugins: {}\n"


def test_nothing_stated_on_a_migrated_install_means_no_sources(
    tmp_path: Path, user_dirs: Path
):
    """Docstrap has no built-in folder name once the installation has moved."""
    _user_config(MIGRATED)
    project = _only(tmp_path / "repo", "version: 1\ntitle: p\n")
    assert project.sources == ()
    assert project.docs_dir is None


def test_the_most_specific_level_wins_whole(tmp_path: Path, user_dirs: Path):
    _user_config(
        "version: 1\nsources:\n  - {path: docs, role: documentation}\n"
        "  - {path: notes, role: planning}\n"
    )
    repo = tmp_path / "repo"
    a, b, c = _projects(
        repo,
        "version: 1\ntitle: r\nsources:\n  - {path: spec, role: planning}\n"
        "projects:\n"
        "  - path: a\n"
        "  - path: b\n    docs_root: manual\n"
        "  - path: c\n    sources: []\n",
    )
    # Repository over installation, and the installation's second entry
    # is not carried along: the lists are not merged.
    assert [(s.stated, s.role) for s in a.sources] == [("spec", "planning")]
    # `docs_root` is the project level's shorthand for one documentation source.
    assert [(s.stated, s.role) for s in b.sources] == [("manual", "documentation")]
    # An empty list is a statement: no sources, and it wins.
    assert c.sources == ()


def test_installation_sources_reach_a_project_that_states_none(
    tmp_path: Path, user_dirs: Path
):
    _user_config("version: 1\nsources:\n  - {path: handbook, role: documentation}\n")
    project = _only(tmp_path / "repo", "version: 1\ntitle: p\n")
    assert project.docs_dir == (tmp_path / "repo" / "handbook").resolve()


def test_a_level_may_not_state_sources_and_docs_root_both(tmp_path: Path):
    config = _write(
        tmp_path / ".docstrap",
        "version: 1\ndocs_root: docs\nsources:\n  - {path: docs, role: documentation}\n",
    )
    with pytest.raises(DocstrapConfigError, match="shorthand"):
        load(config)


def test_a_source_needs_a_role(tmp_path: Path):
    config = _write(tmp_path / ".docstrap", "version: 1\nsources:\n  - {path: docs}\n")
    with pytest.raises(DocstrapConfigError, match="role"):
        load(config)


def test_a_related_directory_stating_neither_field_is_its_own_source(
    tmp_path: Path, user_dirs: Path
):
    _user_config("version: 1\nsources:\n  - {path: docs, role: documentation}\n")
    related = [
        p for p in _projects(
            tmp_path / "repo",
            "version: 1\ntitle: r\nrelated_directories:\n  - {path: notes, title: Notes}\n",
        )
        if p.kind == "related"
    ][0]
    assert related.docs_dir == (tmp_path / "repo" / "notes").resolve()


def test_the_first_source_mounts_at_the_root_and_the_rest_at_their_path(
    tmp_path: Path, user_dirs: Path
):
    project = _only(
        tmp_path / "repo",
        "version: 1\ntitle: p\nsources:\n"
        "  - {path: docs, role: documentation}\n"
        "  - {path: spec, role: planning}\n"
        "  - {path: scratch/ideas, role: draft, mount: ideas}\n",
    )
    assert [(s.stated, s.mount) for s in project.sources] == [
        ("docs", ""), ("spec", "spec"), ("scratch/ideas", "ideas"),
    ]


@pytest.mark.parametrize(
    "sources",
    [
        "  - {path: a, role: documentation}\n  - {path: b, role: planning, mount: ''}\n",
        "  - {path: a, role: documentation}\n  - {path: b, role: x}\n"
        "  - {path: c, role: y, mount: b/c}\n",
    ],
    ids=["two-at-one-mount", "nested-mounts"],
)
def test_mounts_that_would_share_names_are_refused(
    tmp_path: Path, user_dirs: Path, sources: str
):
    with pytest.raises(DocstrapConfigError, match="mount"):
        _only(tmp_path / "repo", f"version: 1\ntitle: p\nsources:\n{sources}")


def test_plugin_enabled_is_tri_state_and_other_keys_merge(tmp_path: Path, user_dirs: Path):
    _user_config(
        "version: 1\nplugins:\n  example:\n    enabled: true\n    colour: blue\n"
        "    size: 3\n"
    )
    a, b = _projects(
        tmp_path / "repo",
        "version: 1\ntitle: r\nplugins:\n  example: {colour: red}\nprojects:\n"
        "  - path: a\n    plugins:\n      example: {enabled: false, size: 9}\n"
        "  - path: b\n",
    )
    inst = settings.installation()
    one = settings.plugin_setting("example", a.project_plugins, a.repository_plugins, inst)
    two = settings.plugin_setting("example", b.project_plugins, b.repository_plugins, inst)
    assert (one.enabled, one.level) == (False, settings.PROJECT)
    assert one.settings == {"colour": "red", "size": 9}
    # The repository spoke about colour but not `enabled`, so it does not
    # out-vote the installation's `true`.
    assert (two.enabled, two.level) == (True, settings.INSTALLATION)
    assert two.settings == {"colour": "red", "size": 3}


def test_a_plugin_nothing_enables_is_off(tmp_path: Path, user_dirs: Path):
    _user_config(MIGRATED)
    project = _only(tmp_path / "repo", "version: 1\ntitle: p\n")
    assert _setting(project).enabled is False
    assert _setting(project).level == settings.DEFAULT


def test_a_plugins_setting_resolves_from_the_plugins_block(
    tmp_path: Path, user_dirs: Path
):
    _user_config(
        "version: 1\nplugins:\n  promdance:\n    enabled: true\n"
        f"    projects_root: {tmp_path}\n"
    )
    a, b = _projects(
        tmp_path / "repo",
        "version: 1\ntitle: r\nprojects:\n"
        "  - path: a\n    plugins:\n      promdance: {enabled: false}\n"
        "  - path: b\n",
    )
    assert (_setting(a).enabled, _setting(a).level) == (False, settings.PROJECT)
    assert (_setting(b).enabled, _setting(b).level) == (True, settings.INSTALLATION)
    assert _projects_root() == str(tmp_path)


def test_an_old_key_after_migration_is_a_load_error_naming_the_command(
    tmp_path: Path, user_dirs: Path
):
    _user_config(MIGRATED + "promdance: true\n")
    with pytest.raises(DocstrapConfigError, match="docstrap config migrate"):
        settings.installation()

    _user_config(MIGRATED)
    with pytest.raises(DocstrapConfigError, match="docstrap config migrate"):
        _projects(tmp_path / "repo", "version: 1\ntitle: r\npromdance: false\n")


# --- roles, in the walk and in the build ---------------------------------------


ROLES_DOCSTRAP = """\
version: 1
title: Roles
sources:
  - {path: docs, role: documentation}
  - {path: spec, role: planning}
  - {path: ideas, role: draft}
"""

ROLES_TREE = {
    "docs/guide.md": "# Guide\n",
    "docs/topics/one.md": "# One\n",
    "spec/design.md": "# Design\n",
    "ideas/maybe.md": "# Maybe\n",
}


def _roles_project(tmp_path: Path):
    repo = tmp_path / "roles"
    for relative, text in ROLES_TREE.items():
        _write(repo / relative, text)
    return _only(repo, ROLES_DOCSTRAP), repo


def test_a_draft_source_is_not_walked_and_others_are_named_by_mount(
    tmp_path: Path, user_dirs: Path
):
    project, repo = _roles_project(tmp_path)
    scope = projectscope.ProjectScope(project=project, config_path=repo / ".docstrap")
    names = sorted(scope.document_slug(d) for d in scope.documents())
    assert names == ["guide", "spec/design", "topics/one"]
    assert scope.document_slug(repo / "ideas" / "maybe.md") is None
    assert scope.document_for_slug("spec/design") == (repo / "spec" / "design.md").resolve()


def test_the_build_mounts_each_source_and_groups_the_landing_page_by_role(
    tmp_path: Path, user_dirs: Path
):
    project, _repo = _roles_project(tmp_path)
    markdown.build(project, tmp_path / "out")

    rows = {e.docname: e for e in fileindex.list_project(project.slug)}
    assert rows["guide"].grouping == "documentation"
    assert rows["spec/design"].grouping == "planning"
    assert rows["ideas/maybe"].grouping == "draft"
    # A mount is not a section: its contents hang off the landing page.
    assert "spec/index" not in rows and "ideas/index" not in rows
    assert rows["spec/design"].parent_docname == "index"

    page = sectionindex.compose(project.slug, "index")
    assert [caption for caption, _ in page.groups] == ["Docs", "Planning", "Drafts"]


def test_the_build_reports_a_project_with_no_sources(tmp_path: Path, user_dirs: Path):
    _user_config(MIGRATED)
    project = _only(tmp_path / "repo", "version: 1\ntitle: p\n")
    result = markdown.build(project, tmp_path / "out")
    assert "no sources stated" in result.notes


# --- 3. round-trip fidelity ----------------------------------------------------


COMMENTED_DOCSTRAP = """\
# The workspace's projects. Keep this comment.
version: 1
title: Workspace   # shown on the store page

projects:
    - path: packages/a      # the first one
      title: A
    - path: packages/b
      title: B
"""


def test_a_plugin_write_keeps_comments_order_and_indentation(
    tmp_path: Path, user_dirs: Path
):
    repo = tmp_path / "ws"
    config = _write(repo / ".docstrap", COMMENTED_DOCSTRAP)
    (repo / "packages" / "a").mkdir(parents=True)

    change = settings.write_plugin_setting(
        settings.PROJECT, repo / "packages" / "a", "promdance", "enabled", False
    )
    text = config.read_text(encoding="utf-8")
    assert change.changed and change.path == config
    for kept in (
        "# The workspace's projects. Keep this comment.",
        "title: Workspace   # shown on the store page",
        "    - path: packages/a      # the first one",
        "    - path: packages/b",
    ):
        assert kept in text
    assert text.index("packages/a") < text.index("packages/b")
    parsed = load(config)
    assert parsed.projects[0].plugins == {"promdance": {"enabled": False}}
    assert parsed.projects[1].plugins is None

    again = settings.write_plugin_setting(
        settings.PROJECT, repo / "packages" / "a", "promdance", "enabled", False
    )
    assert not again.changed
    assert config.read_text(encoding="utf-8") == text


def test_saving_the_stores_list_leaves_the_settings_and_their_comments(
    tmp_path: Path, user_dirs: Path
):
    original = (
        "version: 1\n"
        "# where my stores are\n"
        "stores:\n- /somewhere/.docstrap\n"
        "sources:\n- {path: docs, role: documentation}   # the default\n"
        "plugins:\n  promdance:\n    enabled: true\n"
    )
    _user_config(original)
    store = _write(tmp_path / "s" / ".docstrap", "version: 1\ntitle: s\n")
    user_config.add_store(store)
    text = paths.user_config_file().read_text(encoding="utf-8")
    assert "# where my stores are" in text
    assert "- {path: docs, role: documentation}   # the default" in text
    assert "plugins:\n  promdance:\n    enabled: true\n" in text
    assert str(store.resolve()) in text


def test_an_unchanged_save_leaves_the_file_byte_identical(user_dirs: Path):
    original = "version: 1\nstores:\n- /a/.docstrap\n# trailing note\n"
    _user_config(original)
    user_config.save(user_config.load())
    assert paths.user_config_file().read_text(encoding="utf-8") == original


# --- 4. docstrap config migrate ------------------------------------------------


UNMIGRATED_USER = """\
version: 1
stores:
- {store}
promdance_projects_root: ~/src   # where the repositories are
answers_done_command:
- /bin/notify
"""

UNMIGRATED_STORE = """\
version: 1
title: Store
promdance: false   # off for the whole repository
projects:
  - path: packages/a
    promdance: true
  - path: packages/b
    title: B
"""


def _unmigrated(tmp_path: Path) -> tuple[Path, Path]:
    store = _write(tmp_path / "store" / ".docstrap", UNMIGRATED_STORE)
    user = _user_config(UNMIGRATED_USER.format(store=store))
    return user, store


def _effective(store: Path) -> list[tuple]:
    return [
        (p.slug, tuple((s.stated, s.role, s.mount) for s in p.sources),
         _setting(p).enabled)
        for p in scan(load(store))
    ]


def test_migrate_is_a_dry_run_by_default(tmp_path: Path, user_dirs: Path):
    user, store = _unmigrated(tmp_path)
    before = (user.read_text(encoding="utf-8"), store.read_text(encoding="utf-8"))

    result = runner.invoke(docstrap_app, ["config", "migrate"])

    assert result.exit_code == 0, result.output
    assert (user.read_text(encoding="utf-8"), store.read_text(encoding="utf-8")) == before
    assert f"would change {store}" in result.output
    assert f"would change {user}" in result.output
    assert "+    enabled: true" in result.output
    assert "dry run: nothing written" in result.output


def test_migrate_apply_keeps_every_effective_setting(tmp_path: Path, user_dirs: Path):
    user, store = _unmigrated(tmp_path)
    before = _effective(store)
    root_before = _projects_root()

    result = runner.invoke(docstrap_app, ["config", "migrate", "--apply"])
    assert result.exit_code == 0, result.output
    assert f"changed {store}" in result.output and f"changed {user}" in result.output

    assert settings.installation().migrated
    assert _effective(store) == before
    assert _projects_root() == root_before

    raw = yaml.safe_load(user.read_text(encoding="utf-8"))
    assert "promdance" not in raw and "promdance_projects_root" not in raw
    assert raw["sources"] == [{"path": "docs", "role": "documentation"}]
    assert raw["plugins"]["promdance"] == {
        "enabled": True, "projects_root": "~/src", "members": ["apps/*", "packages/*"],
    }
    assert raw["answers_done_command"] == ["/bin/notify"]
    assert "# where the repositories are" in user.read_text(encoding="utf-8")

    text = store.read_text(encoding="utf-8")
    assert "# off for the whole repository" in text
    parsed = load(store)
    assert parsed.legacy_enabled is None and parsed.plugins == {"promdance": {"enabled": False}}
    assert parsed.projects[0].plugins == {"promdance": {"enabled": True}}
    assert parsed.projects[1].plugins is None


def test_migrate_twice_changes_nothing_the_second_time(tmp_path: Path, user_dirs: Path):
    user, store = _unmigrated(tmp_path)
    assert len(settings.migrate(write=True)) == 2
    after = (user.read_text(encoding="utf-8"), store.read_text(encoding="utf-8"))

    assert settings.migrate(write=True) == []
    assert (user.read_text(encoding="utf-8"), store.read_text(encoding="utf-8")) == after
    result = runner.invoke(docstrap_app, ["config", "migrate"])
    assert "nothing to migrate" in result.output


def test_migrate_turns_absent_into_on_so_the_machine_keeps_its_behaviour(
    tmp_path: Path, user_dirs: Path
):
    store = _write(tmp_path / "store" / ".docstrap", "version: 1\ntitle: s\n")
    _user_config(f"version: 1\nstores:\n- {store}\n")
    project = list(scan(load(store)))[0]
    assert _setting(project).enabled is True

    settings.migrate(write=True)

    project = list(scan(load(store)))[0]
    assert (_setting(project).enabled, _setting(project).level) == (
        True, settings.INSTALLATION,
    )
    assert project.sources[0].stated == "docs"


def test_migrate_leaves_a_stated_off_off(tmp_path: Path, user_dirs: Path):
    _user_config("version: 1\nstores: []\npromdance: false\n")
    settings.migrate(write=True)
    assert _installation_stated() is False


def test_the_sources_type_round_trips(tmp_path: Path):
    """`Source` is what both levels parse into."""
    config = _write(
        tmp_path / ".docstrap",
        "version: 1\nsources:\n  - {path: a, role: notes, mount: n}\n",
    )
    assert load(config).sources == (Source(path="a", role="notes", mount="n"),)

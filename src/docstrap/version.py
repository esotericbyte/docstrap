"""Runtime version and install-origin reporting for docstrap."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VersionInfo:
    version: str
    install_kind: str
    executable: str
    ref: str | None = None
    commit: str | None = None
    source: str | None = None


def get_version_info() -> VersionInfo:
    """Return package version plus enough origin data to identify the binary."""
    version = metadata.version("docstrap")
    executable = str(Path(sys.argv[0]).resolve())
    direct_url = _read_direct_url()

    if direct_url:
        vcs_info = direct_url.get("vcs_info") or {}
        dir_info = direct_url.get("dir_info") or {}
        source = direct_url.get("url")

        if vcs_info:
            return VersionInfo(
                version=version,
                install_kind="stable",
                executable=executable,
                ref=vcs_info.get("requested_revision") or vcs_info.get("commit_id"),
                commit=vcs_info.get("commit_id"),
                source=source,
            )

        if dir_info.get("editable"):
            return VersionInfo(
                version=version,
                install_kind="workspace-dev",
                executable=executable,
                source=source,
            )

    return VersionInfo(
        version=version,
        install_kind="unknown",
        executable=executable,
        source=direct_url.get("url") if direct_url else None,
    )


def format_version_info(info: VersionInfo | None = None) -> str:
    """Format version info for humans and scripts."""
    info = info or get_version_info()
    lines = [
        f"docstrap {info.version}",
        f"install: {info.install_kind}",
        f"executable: {info.executable}",
    ]
    if info.ref:
        lines.append(f"ref: {info.ref}")
    if info.commit and info.commit != info.ref:
        lines.append(f"commit: {info.commit}")
    if info.source:
        lines.append(f"source: {info.source}")
    return "\n".join(lines)


def _read_direct_url() -> dict[str, Any] | None:
    try:
        dist = metadata.distribution("docstrap")
        direct_url_text = dist.read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return None
    if not direct_url_text:
        return None
    try:
        value = json.loads(direct_url_text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None

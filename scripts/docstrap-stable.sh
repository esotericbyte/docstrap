#!/usr/bin/env bash
# Install or remove the stable docstrap PATH command.
#
# Dev remains:    uv run docstrap
# Stable becomes: ~/.local/bin/docstrap, installed by uv tool from a git ref
# of this repository, isolated from the live working tree. Promdance,
# docstrap's plugin, is not part of this repository; when PROMDANCE_SOURCE
# names it, it goes into the same tool environment so docstrap can load it,
# and its own command is exposed beside docstrap's (plan 0002 §6).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL_NAME="docstrap"
PROMDANCE_SOURCE="${PROMDANCE_SOURCE:-}"
RESOLVED_REF=""

usage() {
  cat <<'EOF'
Usage:
  scripts/docstrap-stable.sh install [REF]
  scripts/docstrap-stable.sh remove
  scripts/docstrap-stable.sh --help

REF is a ref of this repository (docstrap). Installs the stable docstrap
command with:
  uv tool install --force "docstrap @ git+file://<repo>@<ref>"

When PROMDANCE_SOURCE is set, promdance, docstrap's plugin, joins the same
tool environment and its command goes on PATH:
  uv tool install --force "docstrap @ git+file://<repo>@<ref>" \
    --with-executables-from "promdance @ $PROMDANCE_SOURCE"

PROMDANCE_SOURCE is a uv direct-reference URL, for example
  git+file:///path/to/checkout@<ref>#subdirectory=packages/promdance

The workspace development command is unchanged:
  uv run docstrap

Stable installs are for dogfooding a pinned repository ref through
~/.local/bin/docstrap without running the current working copy.

If REF is omitted, the script uses the most recent git tag. If no tag
exists yet, it refuses and asks for an explicit ref or a real tag.

For isolated validation, set UV_TOOL_DIR, UV_TOOL_BIN_DIR, and PATH before
running this script. The normal dogfood path needs no extra variables.
EOF
}

die() {
  echo "docstrap-stable: $*" >&2
  exit 2
}

latest_tag() {
  git -C "$REPO_ROOT" for-each-ref --sort=-creatordate --count=1 \
    --format='%(refname:short)' refs/tags | grep .
}

resolve_ref() {
  local requested="${1:-}"
  if [[ -n "$requested" ]]; then
    git -C "$REPO_ROOT" rev-parse --verify --quiet "${requested}^{commit}" >/dev/null \
      || die "ref not found: $requested"
    RESOLVED_REF="$requested"
    return 0
  fi

  if RESOLVED_REF="$(latest_tag)"; then
    return 0
  fi

  die "no tag exists yet; pass an explicit git ref, or tag a release"
}

print_on_path() {
  local path
  local version_output
  local version
  local ref
  if ! path="$(command -v "$TOOL_NAME" 2>/dev/null)"; then
    die "$TOOL_NAME is installed, but no '$TOOL_NAME' command is on PATH; add ${UV_TOOL_BIN_DIR:-$HOME/.local/bin} to PATH"
  fi
  version_output="$("$path" --version)"
  version="$(awk '/^docstrap / {print $2; exit}' <<<"$version_output")"
  ref="$(awk '/^ref: / {print $2; exit}' <<<"$version_output")"
  echo "path: $path"
  echo "version: ${version:-unknown}"
  echo "ref: ${ref:-unknown}"
  echo "$version_output"
}

install_stable() {
  local ref="$1"
  local docstrap_spec="docstrap @ git+file://$REPO_ROOT@$ref"
  local with=()
  if [[ -n "$PROMDANCE_SOURCE" ]]; then
    echo "installing stable docstrap from ref: $ref, with promdance from $PROMDANCE_SOURCE"
    with=(--with-executables-from "promdance @ $PROMDANCE_SOURCE")
  else
    echo "installing stable docstrap from ref: $ref (PROMDANCE_SOURCE unset: no plugin)"
  fi
  uv tool install --force "$docstrap_spec" "${with[@]}"
  echo
  print_on_path
}

remove_stable() {
  uv tool uninstall "$TOOL_NAME"
  echo "removed stable docstrap"
}

main() {
  local command="${1:-}"
  case "$command" in
    install)
      shift
      [[ "$#" -le 1 ]] || die "install accepts at most one REF"
      resolve_ref "${1:-}"
      install_stable "$RESOLVED_REF"
      ;;
    remove|uninstall)
      shift
      [[ "$#" -eq 0 ]] || die "$command accepts no arguments"
      remove_stable
      ;;
    -h|--help|help)
      usage
      ;;
    "")
      usage
      exit 2
      ;;
    *)
      die "unknown command: $command"
      ;;
  esac
}

main "$@"

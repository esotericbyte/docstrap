#!/usr/bin/env bash
# Install or remove the stable docstrap PATH command.
#
# Dev remains:    uv run docstrap
# Stable becomes: ~/.local/bin/docstrap, installed by uv tool from a pinned
# git ref, isolated from the live working tree. Docstrap comes from its own
# repository, at the commit this repository's promdance pins. Promdance,
# docstrap's plugin, comes from this repository and goes into the same tool
# environment so docstrap can load it, and its own command is exposed beside
# docstrap's (plan 0002 §6).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCSTRAP_REPO="https://github.com/esotericbyte/docstrap"
PLUGIN_SUBDIR="packages/promdance"
TOOL_NAME="docstrap"
RESOLVED_REF=""

usage() {
  cat <<'EOF'
Usage:
  scripts/docstrap-stable.sh install [REF]
  scripts/docstrap-stable.sh remove
  scripts/docstrap-stable.sh --help

REF is a ref of this repository (platformshoes). Installs the stable
docstrap command with:
  uv tool install --force "docstrap @ git+https://github.com/esotericbyte/docstrap@<pin>" \
    --with-executables-from "promdance @ git+file://<repo>@<ref>#subdirectory=packages/promdance"

where <pin> is the docstrap commit that packages/promdance/pyproject.toml
pins at REF ([tool.uv.sources] docstrap rev). That puts promdance, docstrap's
plugin, in docstrap's tool environment and its command on PATH. A ref from
before docstrap left this repository has no such pin and is refused.

The workspace development command is unchanged:
  uv run docstrap

Stable installs are for dogfooding a pinned repository ref through
~/.local/bin/docstrap without running the current working copy.

If REF is omitted, the script uses the most recent git tag that contains
packages/promdance. If no such tag exists yet, it refuses and asks for an
explicit ref or a real tag.

For isolated validation, set UV_TOOL_DIR, UV_TOOL_BIN_DIR, and PATH before
running this script. The normal dogfood path needs no extra variables.
EOF
}

die() {
  echo "docstrap-stable: $*" >&2
  exit 2
}

latest_promdance_tag() {
  local tag
  while IFS= read -r tag; do
    if git -C "$REPO_ROOT" cat-file -e "$tag:$PLUGIN_SUBDIR/pyproject.toml" 2>/dev/null; then
      printf '%s\n' "$tag"
      return 0
    fi
  done < <(git -C "$REPO_ROOT" for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags)
  return 1
}

resolve_ref() {
  local requested="${1:-}"
  if [[ -n "$requested" ]]; then
    git -C "$REPO_ROOT" rev-parse --verify --quiet "${requested}^{commit}" >/dev/null \
      || die "ref not found: $requested"
    git -C "$REPO_ROOT" cat-file -e "$requested:$PLUGIN_SUBDIR/pyproject.toml" 2>/dev/null \
      || die "ref '$requested' does not contain $PLUGIN_SUBDIR"
    RESOLVED_REF="$requested"
    return 0
  fi

  if RESOLVED_REF="$(latest_promdance_tag)"; then
    return 0
  fi

  die "no tag containing $PLUGIN_SUBDIR exists yet; pass an explicit git ref, or tag a release"
}

# The docstrap commit promdance pins at REF, read from its pyproject.toml.
docstrap_pin() {
  local ref="$1"
  git -C "$REPO_ROOT" show "$ref:$PLUGIN_SUBDIR/pyproject.toml" | python3 -c '
import sys, tomllib
source = tomllib.load(sys.stdin.buffer).get("tool", {}).get("uv", {}).get("sources", {}).get("docstrap", {})
if source.get("git") and source.get("rev"):
    print(source["rev"])
'
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
  local repo_url="file://$REPO_ROOT"
  local pin
  pin="$(docstrap_pin "$ref")"
  [[ -n "$pin" ]] \
    || die "ref '$ref' pins no docstrap commit in $PLUGIN_SUBDIR/pyproject.toml; it predates docstrap's own repository"

  echo "installing stable docstrap $pin with promdance from ref: $ref"
  uv tool install --force "docstrap @ git+$DOCSTRAP_REPO@$pin" \
    --with-executables-from "promdance @ git+$repo_url@$ref#subdirectory=$PLUGIN_SUBDIR"
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

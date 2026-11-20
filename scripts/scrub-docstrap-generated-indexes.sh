#!/usr/bin/env bash
# One-time cleanup for docstrap-generated index.md files.
#
# Dry-run first:
#   scripts/scrub-docstrap-generated-indexes.sh /path/to/repo /path/to/another-repo
#   scripts/scrub-docstrap-generated-indexes.sh --root /path/holding/repos
#
# Apply only after reviewing the dry-run report:
#   scripts/scrub-docstrap-generated-indexes.sh --apply /path/to/repo
#   scripts/scrub-docstrap-generated-indexes.sh --apply --root /path/holding/repos
#
# The script asks `docstrap generated-indexes --json` which files docstrap
# claims. It removes only claimed files named index.md. Deletions are staged
# with `git rm` and are not committed or pushed, leaving each repository ready
# for human review and a local commit.
set -euo pipefail

DOCSTRAP_BIN="${DOCSTRAP_BIN:-docstrap}"

usage() {
  cat <<'EOF'
Usage:
  scripts/scrub-docstrap-generated-indexes.sh [--apply] REPO...
  scripts/scrub-docstrap-generated-indexes.sh [--apply] --root ROOT
  scripts/scrub-docstrap-generated-indexes.sh --help

Dry-run is the default. It reports the files docstrap claims, grouped by
repository, and changes nothing.

With --apply, the script removes only those claimed files with `git rm`, so
the deletions are staged but not committed. It skips any repository with a
dirty tracked tree.

Set DOCSTRAP_BIN to choose a docstrap executable. It defaults to `docstrap`.
EOF
}

die() {
  echo "scrub-docstrap-generated-indexes: $*" >&2
  exit 2
}

apply=0
root=""
inputs=()

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --apply)
      apply=1
      shift
      ;;
    --root)
      [[ "$#" -ge 2 ]] || die "--root needs a directory"
      root="$2"
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ "$#" -gt 0 ]]; do
        inputs+=("$1")
        shift
      done
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      inputs+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$root" && "${#inputs[@]}" -gt 0 ]]; then
  die "pass repositories as arguments, or pass --root, not both"
fi

repo_candidates=()
if [[ -n "$root" ]]; then
  [[ -d "$root" ]] || die "root is not a directory: $root"
  while IFS= read -r git_entry; do
    repo_candidates+=("$(dirname "$git_entry")")
  done < <(find "$root" -name .git -print | sort)
else
  [[ "${#inputs[@]}" -gt 0 ]] || die "pass at least one repository, or --root ROOT"
  repo_candidates=("${inputs[@]}")
fi

if ! command -v "$DOCSTRAP_BIN" >/dev/null 2>&1; then
  die "docstrap command not found: $DOCSTRAP_BIN"
fi

normalize_repo() {
  local candidate="$1"
  git -C "$candidate" rev-parse --show-toplevel 2>/dev/null
}

tracked_index_files() {
  local repo="$1"
  local path
  while IFS= read -r -d '' path; do
    [[ "$(basename "$path")" == "index.md" ]] || continue
    printf '%s\n' "$path"
  done < <(git -C "$repo" ls-files -z)
}

discover_project_docs() {
  local repo="$1"
  local config="$repo/.docstrap"
  [[ -f "$config" ]] || return 0
  "$DOCSTRAP_BIN" scan --config "$config" | sed -n 's/^    docs: //p' | sort -u
}

json_records() {
  local repo="$1"
  local json="$2"
  JSON_PAYLOAD="$json" python3 - "$repo" <<'PY'
import json
import os
from pathlib import Path
import sys

repo = Path(sys.argv[1]).resolve()
payload = json.loads(os.environ["JSON_PAYLOAD"])
for finding in payload.get("findings", []):
    path = Path(finding["path"]).resolve()
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError:
        rel = ""
    print(
        "\t".join(
            [
                rel,
                finding.get("state", ""),
                finding.get("display", ""),
                "1" if finding.get("docstrap_wrote_it") else "0",
                str(path),
            ]
        )
    )
PY
}

unique_repos=()
seen_repos=""
for candidate in "${repo_candidates[@]}"; do
  repo="$(normalize_repo "$candidate")" || die "not a git repository: $candidate"
  case $'\n'"$seen_repos"$'\n' in
    *$'\n'"$repo"$'\n'*) ;;
    *)
      unique_repos+=("$repo")
      seen_repos+="${repo}"$'\n'
      ;;
  esac
done

mode="dry-run"
if [[ "$apply" -eq 1 ]]; then
  mode="apply"
fi
echo "mode: $mode"
echo "deletion strategy: git rm stages removals; this script does not commit or push"
echo

had_problem=0
total_remove=0

for repo in "${unique_repos[@]}"; do
  echo "repository: $repo"

  if [[ -n "$(git -C "$repo" status --porcelain --untracked-files=no)" ]]; then
    echo "  SKIPPED: dirty tracked tree"
    echo
    had_problem=1
    continue
  fi

  declare -A tracked=()
  declare -A reported=()
  declare -A removable=()
  declare -A unclaimed=()
  declare -A unsafe_claims=()
  declare -A retired=()

  while IFS= read -r index_path; do
    [[ -n "$index_path" ]] || continue
    tracked["$index_path"]=1
  done < <(tracked_index_files "$repo")

  if [[ ! -f "$repo/.docstrap" ]]; then
    echo "  no .docstrap config; cannot ask docstrap to classify this repository"
  else
    if ! scan_output="$(discover_project_docs "$repo")"; then
      echo "  ERROR: docstrap scan failed for $repo/.docstrap"
      had_problem=1
      scan_output=""
    fi
    mapfile -t project_docs < <(printf '%s\n' "$scan_output" | sed '/^$/d')
    if [[ "${#project_docs[@]}" -eq 0 ]]; then
      echo "  no docstrap projects found"
    fi

    for docs_path in "${project_docs[@]}"; do
      [[ -n "$docs_path" ]] || continue
      if ! json="$("$DOCSTRAP_BIN" generated-indexes "$docs_path" --json)"; then
        echo "  ERROR: docstrap generated-indexes failed for $docs_path"
        had_problem=1
        continue
      fi
      if ! records="$(json_records "$repo" "$json")"; then
        echo "  ERROR: could not parse docstrap generated-indexes JSON for $docs_path"
        had_problem=1
        continue
      fi
      while IFS=$'\t' read -r rel state display is_docstrap abs_path; do
        [[ -n "$rel$state$display$is_docstrap$abs_path" ]] || continue
        [[ -n "$rel" ]] || {
          echo "  not touched: $abs_path (outside repository)"
          had_problem=1
          continue
        }
        reported["$rel"]=1
        if [[ "$rel" == "docs-site/index.md" && "$is_docstrap" == "1" ]]; then
          echo "  FATAL: docstrap claimed authored page docs-site/index.md"
          echo "  Stop here; generated-indexes is wrong for this repository."
          exit 2
        fi
        if [[ "$(basename "$rel")" != "index.md" ]]; then
          unsafe_claims["$rel"]="docstrap claimed a non-index.md path; not touched"
          continue
        fi
        if [[ "$(basename "$repo")" == "rlp" && "$rel" == "docs/adr/index.md" ]]; then
          retired["$rel"]="Log4brains residue from a retired tool; not touched"
        fi
        if [[ "$is_docstrap" == "1" ]]; then
          removable["$rel"]=1
        else
          unclaimed["$rel"]="$state; docstrap does not claim this file"
        fi
      done <<<"$records"
    done
  fi

  for rel in "${!tracked[@]}"; do
    [[ -n "${reported[$rel]:-}" ]] && continue
    unclaimed["$rel"]="not reported by docstrap generated-indexes"
    if [[ "$(basename "$repo")" == "rlp" && "$rel" == "docs/adr/index.md" ]]; then
      retired["$rel"]="Log4brains residue from a retired tool; not touched"
    fi
  done

  mapfile -t remove_list < <(printf '%s\n' "${!removable[@]}" | sed '/^$/d' | sort)
  mapfile -t unsafe_list < <(printf '%s\n' "${!unsafe_claims[@]}" | sed '/^$/d' | sort)
  mapfile -t retired_list < <(printf '%s\n' "${!retired[@]}" | sed '/^$/d' | sort)
  mapfile -t unclaimed_list < <(printf '%s\n' "${!unclaimed[@]}" | sed '/^$/d' | sort)

  echo "  claimed generated index.md files: ${#remove_list[@]}"
  if [[ "${#remove_list[@]}" -gt 0 ]]; then
    for rel in "${remove_list[@]}"; do
      if [[ "$apply" -eq 1 ]]; then
        git -C "$repo" rm --quiet -- "$rel"
      else
        echo "    would remove: $rel"
      fi
    done
    if [[ "$apply" -eq 1 ]]; then
      echo "    removed and staged: ${#remove_list[@]} file(s)"
    fi
  fi

  if [[ "${#retired_list[@]}" -gt 0 ]]; then
    echo "  retired-tool file(s), not touched:"
    for rel in "${retired_list[@]}"; do
      echo "    $rel - ${retired[$rel]}"
    done
  fi

  if [[ "${#unsafe_list[@]}" -gt 0 ]]; then
    echo "  unsafe docstrap claim(s), not touched:"
    for rel in "${unsafe_list[@]}"; do
      echo "    $rel - ${unsafe_claims[$rel]}"
    done
  fi

  if [[ "${#unclaimed_list[@]}" -gt 0 ]]; then
    echo "  unclassified or unclaimed index.md files, not touched:"
    for rel in "${unclaimed_list[@]}"; do
      echo "    $rel - ${unclaimed[$rel]}"
    done
  fi

  total_remove=$((total_remove + ${#remove_list[@]}))
  echo
done

if [[ "$apply" -eq 1 ]]; then
  echo "total removed and staged: $total_remove"
else
  echo "total that would be removed: $total_remove"
fi

if [[ "$had_problem" -ne 0 ]]; then
  exit 1
fi

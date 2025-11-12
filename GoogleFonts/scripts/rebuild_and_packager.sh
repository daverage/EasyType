#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:-}"
COMMIT="${2:-HEAD}"

if [[ -z "$REPO_PATH" ]]; then
  echo "Usage: $0 /path/to/google/fonts [commit]"
  exit 1
fi

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "GH_TOKEN must be set before running this script."
  exit 1
fi

FAMILIES=(
  "EasyType Sans"
  "EasyType Focus"
  "EasyType Dyslexic"
)

SLUGS=(
  easytypesans
  easytypefocus
  easytypedyslexic
)

# regenerate metadata for each family
python3 scripts/generate_packager_metadata.py "$REPO_PATH" --commit "$COMMIT"

# rerun packager for each family (clean the matching slug first)
for i in "${!FAMILIES[@]}"; do
  family="${FAMILIES[i]}"
  slug="${SLUGS[i]}"
  target="$REPO_PATH/ofl/$slug"
  if [[ -d "$target" ]]; then
    rm -rf "$target"
    echo "Removed stale $target"
  fi
  echo "Running gftools packager for $family"
  gftools packager "$family" "$REPO_PATH"
done

echo "Packager automation completed."

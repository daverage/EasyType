#!/usr/bin/env bash
set -euo pipefail

# Run Fontbakery's Google Fonts profile against the generated TTF builds.
# Invoked from `gf/sources/`, so we resolve the repo root relative to this script.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BINDIR="$ROOT/../fonts/ttf"

families=(
  EasyTypeSans
  EasyTypeFocus
  EasyTypeDyslexic
)

if ! command -v fontbakery &> /dev/null; then
  echo "fontbakery is not installed. Run 'pip install fontbakery' first." >&2
  exit 1
fi

for family in "${families[@]}"; do
  family_lower="$(printf "%s" "$family" | tr '[:upper:]' '[:lower:]')"
  html_report="$ROOT/documentation/fontbakery-report-${family_lower}.html"
  echo "Running Fontbakery for ${family} (report -> ${html_report})"
  fontbakery check-googlefonts "$BINDIR/${family}-"*.ttf --html "$html_report"
done

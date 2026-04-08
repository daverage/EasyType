#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_PATH="$ROOT_DIR/fonts/build_report.json"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Missing required dependency: python3" >&2
  exit 1
fi

if ! python3 -c "import fontTools" >/dev/null 2>&1; then
  echo "Missing required dependency: fontTools. Install with 'pip install fonttools'." >&2
  exit 1
fi

if ! command -v ttfautohint >/dev/null 2>&1; then
  echo "Warning: ttfautohint not found; build will continue without hinting unless installed." >&2
fi

if ! command -v woff2_compress >/dev/null 2>&1; then
  echo "Warning: woff2_compress not found; build will continue without webfont compression." >&2
fi

cd "$ROOT_DIR"
python3 "Generator Tools/font.py" "$@"

if [[ -f "$REPORT_PATH" ]]; then
  python3 - "$REPORT_PATH" <<'PY'
import json
import sys

report_path = sys.argv[1]
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)

families = ", ".join(report.get("families", {}).keys()) or "none"
version = report.get("version", "unknown")
print(f"Build complete: version {version}; families: {families}")
PY
fi

#!/usr/bin/env python3
"""
Subset and recompress webfonts in-place using fontTools' pyftsubset.

Example:
    python tools/compress_webfonts.py \
        --fonts-dir fonts/web \
        --unicode-range "U+0000-00FF" \
        --text-source test/data/passages.json

The script requires `pyftsubset` (fonttools>=4) to be installed and on PATH.
"""
from __future__ import annotations

import argparse
import shutil
import string
import subprocess
import sys
from pathlib import Path

DEFAULT_UNICODE_RANGE = "U+0000-00FF"
FONT_EXTENSIONS = (".ttf", ".otf", ".woff", ".woff2")


def build_character_set(text_files: list[Path]) -> str:
    chars = set(string.printable)
    for file_path in text_files:
        try:
            chars.update(file_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            print(f"[warn] Could not read {file_path}: {exc}", file=sys.stderr)
    return "".join(sorted(chars))


def subset_font(
    source: Path,
    dest: Path,
    unicode_range: str,
    chars: str | None,
    layout_features: str,
    drop_tables: tuple[str, ...],
    passthrough_tables: tuple[str, ...],
    no_hinting: bool,
    desubroutinize: bool,
    dry_run: bool,
) -> None:
    cmd = [
        "pyftsubset",
        str(source),
        f"--output-file={dest}",
        "--flavor=woff2",
        "--with-zopfli",
        f"--layout-features={layout_features}",
    ]
    if drop_tables:
        cmd.append(f"--drop-tables={','.join(drop_tables)}")
    if passthrough_tables:
        cmd.append(f"--passthrough-tables={','.join(passthrough_tables)}")
    if no_hinting:
        cmd.append("--no-hinting")
    if desubroutinize:
        cmd.append("--desubroutinize")
    if chars:
        cmd.append(f"--text={chars}")
    else:
        cmd.append(f"--unicodes={unicode_range}")

    print(f"[info] {' '.join(cmd)}")
    if dry_run:
        return

    subprocess.run(cmd, check=True)
    shutil.move(dest, source)


def main() -> None:
    parser = argparse.ArgumentParser(description="Subset/compress fonts to WOFF2.")
    parser.add_argument(
        "--fonts-dir",
        default="fonts/web",
        type=Path,
        help="Directory containing fonts to recompress (default: fonts/web).",
    )
    parser.add_argument(
        "--unicode-range",
        default=DEFAULT_UNICODE_RANGE,
        help="Unicode range passed to pyftsubset when --text-source is not provided.",
    )
    parser.add_argument(
        "--text-source",
        action="append",
        type=Path,
        help="Optional file whose text should define the glyph set (can be repeated).",
    )
    parser.add_argument(
        "--layout-features",
        default="*",
        help="Layout features to keep (default: '*').",
    )
    parser.add_argument(
        "--drop-tables",
        default="DSIG,FFTM",
        help="Comma-separated list of tables to drop for smaller files (default drops signature/FFTM metadata).",
    )
    parser.add_argument(
        "--passthrough-tables",
        default="",
        help="Comma-separated list of tables to keep verbatim (e.g. COLR,CPAL).",
    )
    parser.add_argument(
        "--no-hinting",
        action="store_true",
        help="Strip TrueType hinting data (improves compression, safe for modern browsers).",
    )
    parser.add_argument(
        "--desubroutinize",
        action="store_true",
        help="Apply --desubroutinize to normalize CFF outlines before compression.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without modifying any fonts.",
    )
    args = parser.parse_args()

    if shutil.which("pyftsubset") is None:
        parser.error("pyftsubset not found on PATH. Install fonttools to continue.")

    fonts_dir: Path = args.fonts_dir
    if not fonts_dir.exists():
        parser.error(f"Fonts directory {fonts_dir} does not exist.")

    text_files = args.text_source or []
    chars = build_character_set(text_files) if text_files else None

    font_files = [
        path for path in fonts_dir.iterdir() if path.suffix.lower() in FONT_EXTENSIONS
    ]
    if not font_files:
        parser.error(f"No fonts with extensions {FONT_EXTENSIONS} found in {fonts_dir}.")

    temp_output = fonts_dir / ".subset-temp.woff2"
    for font_path in font_files:
        subset_font(
            source=font_path,
            dest=temp_output,
            unicode_range=args.unicode_range,
            chars=chars,
            layout_features=args.layout_features,
            drop_tables=tuple(part.strip() for part in args.drop_tables.split(",") if part.strip()),
            passthrough_tables=tuple(
                part.strip() for part in args.passthrough_tables.split(",") if part.strip()
            ),
            no_hinting=args.no_hinting,
            desubroutinize=args.desubroutinize,
            dry_run=args.dry_run,
        )
    print("[done] Fonts have been subset and recompressed.")


if __name__ == "__main__":
    main()

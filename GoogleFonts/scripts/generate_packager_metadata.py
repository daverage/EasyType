#!/usr/bin/env python3
"""Emit METADATA.pb files for the EasyType families inside an existing google/fonts clone."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

BUILDER_ROOT = Path(__file__).resolve().parents[1]

FAMILY_STYLES = [
    {"label": "Regular", "suffix": "Regular", "style": "normal", "weight": 400},
    {"label": "Italic", "suffix": "Italic", "style": "italic", "weight": 400},
    {"label": "Bold", "suffix": "Bold", "style": "normal", "weight": 700},
    {"label": "Bold Italic", "suffix": "BoldItalic", "style": "italic", "weight": 700},
]

FAMILY_DATA = {
    "EasyType Sans": {"slug": "easytypesans"},
    "EasyType Focus": {"slug": "easytypefocus"},
    "EasyType Dyslexic": {"slug": "easytypedyslexic"},
}

COMMON_SUBSETS = ["latin", "latin-ext", "greek", "cyrillic"]
DESIGNER = "Andrzej Marczewski"
LICENSE = "OFL"
CATEGORY = "SANS_SERIF"
DATE_ADDED = "2025-03-01"
REPOSITORY_URL = "https://github.com/daverage/EasyType"
ARCHIVE_URL = "https://github.com/daverage/EasyType/archive/refs/heads/main.zip"
PRIMARY_SCRIPT = "Latn"
COPYRIGHT_LINE = "Copyright 2025 The EasyType Project Authors (https://github.com/daverage/EasyType)"
SOURCE_FILES = [
    ("OFL.txt", "OFL.txt"),
    ("documentation/article/ARTICLE.en_us.html", "article/ARTICLE.en_us.html"),
]


def builder_file(path: str) -> Path:
    target = BUILDER_ROOT / path
    if not target.exists():
        sys.exit(f"Missing required builder file: {target}")
    return target


def format_fonts(family_name: str) -> list[str]:
    base = family_name.replace(" ", "")
    lines: list[str] = []
    for spec in FAMILY_STYLES:
        filename = f"{base}-{spec['suffix']}.ttf"
        post_script = filename.replace(".ttf", "")
        lines.extend(
            [
                "fonts {",
                f'  name: "{family_name}"',
                f'  style: "{spec["style"]}"',
                f'  weight: {spec["weight"]}',
                f'  filename: "{filename}"',
                f'  post_script_name: "{post_script}"',
                f'  full_name: "{family_name} {spec["label"]}"',
                f'  copyright: "{COPYRIGHT_LINE}"',
                "}",
            ]
        )
    return lines


def format_source(files: list[tuple[str, str]], args: argparse.Namespace) -> list[str]:
    lines = ["source {"]
    lines.append(f'  repository_url: "{REPOSITORY_URL}"')
    lines.append(f'  branch: "{args.branch}"')
    if args.commit:
        lines.append(f'  commit: "{args.commit}"')
    if args.archive_url:
        lines.append(f'  archive_url: "{args.archive_url}"')
    for source_file, dest_file in files:
        # Ensure the source exists to catch typos early.
        builder_file(source_file)
        lines.extend(
            [
                "  files {",
                f'    source_file: "{source_file}"',
                f'    dest_file: "{dest_file}"',
                "  }",
            ]
        )
    lines.append("}")
    return lines


def build_metadata(family_name: str, data: dict, args: argparse.Namespace) -> str:
    lines = [
        f'name: "{family_name}"',
        f'designer: "{DESIGNER}"',
        f'license: "{LICENSE}"',
        f'category: "{CATEGORY}"',
        f'date_added: "{DATE_ADDED}"',
    ]
    lines.extend(format_fonts(family_name))
    for subset in COMMON_SUBSETS:
        lines.append(f'subsets: "{subset}"')
    lines.append(f'primary_script: "{PRIMARY_SCRIPT}"')
    lines.extend(format_source(files=data["source_files"], args=args))
    return "\n".join(lines) + "\n"


def gather_source_files(family_name: str) -> list[tuple[str, str]]:
    base = family_name.replace(" ", "")
    extra_files = []
    for spec in FAMILY_STYLES:
        filename = f"fonts/ttf/{base}-{spec['suffix']}.ttf"
        extra_files.append((filename, filename.split("/")[-1]))
    extra_files.extend(SOURCE_FILES)
    return extra_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate METADATA.pb entries for EasyType families inside a local google/fonts clone."
    )
    parser.add_argument(
        "google_fonts_path",
        type=Path,
        help="Path to the cloned google/fonts repository",
    )
    parser.add_argument(
        "--commit",
        help="Git commit (or tag) that represents the source state",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch name to reference inside the source block (default: main)",
    )
    parser.add_argument(
        "--archive-url",
        default=ARCHIVE_URL,
        help="Archive URL for the EasyType sources (default: GitHub main archive)",
    )
    args = parser.parse_args()

    for family_name, meta in FAMILY_DATA.items():
        meta["source_files"] = gather_source_files(family_name)
        metadata = build_metadata(family_name, meta, args)
        dest = args.google_fonts_path / "ofl" / meta["slug"]
        dest.mkdir(parents=True, exist_ok=True)
        target_file = dest / "METADATA.pb"
        target_file.write_text(metadata, encoding="utf-8")
        print(f"Wrote {target_file}")


if __name__ == "__main__":
    main()

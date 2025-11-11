#!/usr/bin/env python3
from pathlib import Path
import re
import html

ROOT = Path(__file__).resolve().parent.parent
REPORTS = sorted((ROOT / "documentation").glob("fontbakery-report-*.html"))

TRIGGERS = {
    "mark_glyphs": "The following mark characters could be in the GDEF mark glyph class:",
    "spacing_marks": "The following glyphs seem to be spacing",
}


def glyphs_from(snippet):
    return re.findall(r"([\w]+) \(U\+[0-9A-F]+\)", snippet)


def find_sections(text, trigger):
    start = 0
    while True:
        idx = text.find(trigger, start)
        if idx == -1:
            break
        end = text.find("Result: WARN", idx)
        snippet = text[idx:end] if end != -1 else text[idx:]
        yield snippet
        start = end if end != -1 else idx + len(trigger)


def summarize(report_path):
    text = html.unescape(report_path.read_text())
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain)
    print(f"\n{report_path.name}")
    for label, trigger in TRIGGERS.items():
        entries = list(find_sections(plain, trigger))
        if not entries:
            continue
        for entry in entries:
            glyphs = glyphs_from(entry)
            count = len(glyphs)
            sample = ", ".join(glyphs[:20])
            more = f", ... (+{count - 20} more)" if count > 20 else ""
            print(f"  {label} ({count} glyphs): {sample}{more}")


def main():
    if not REPORTS:
        print("No Fontbakery reports found.")
        return
    for report in REPORTS:
        summarize(report)


if __name__ == "__main__":
    main()

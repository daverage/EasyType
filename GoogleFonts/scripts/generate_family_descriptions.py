#!/usr/bin/env python3
"""Create per-family DESCRIPTION.en_us.html files derived from the main article."""

from pathlib import Path

OUTPUT_DIR = Path("documentation/article-descriptions")

FAMILIES = {
    "EasyType Sans": {
        "slug": "easytypesans",
        "summary": (
            "EasyType Sans is the balanced workhorse of the trio, tuned for interfaces, "
            "editorial work, and educational layouts. It keeps the familiar Noto proportions "
            "but adds optical anchoring and a raised x-height so every word starts from a "
            "consistent visual landmark."
        ),
    },
    "EasyType Focus": {
        "slug": "easytypefocus",
        "summary": (
            "EasyType Focus is engineered for focused reading: each letter and word spacing "
            "is looser, the counters breathe easier, and the gentle micro-spacing keeps "
            "lines composed even when attention drifts."
        ),
    },
    "EasyType Dyslexic": {
        "slug": "easytypedyslexic",
        "summary": (
            "EasyType Dyslexic maximizes openness, with sculpted apertures, wider bowls, "
            "and generous weights that keep each glyph distinct even when the eyes tire."
        ),
    },
}

CONTRIBUTION_PARAGRAPH = (
    "Designed and documented by Andrzej Marczewski, the EasyType builder script "
    "and QA notes live in the GitHub repository so every change is reproducible. "
    "To contribute or explore the tooling, visit "
    "<a href=\"https://github.com/daverage/EasyType\">github.com/daverage/EasyType</a>."
)


def build_html(family_name: str, summary: str) -> str:
    return (
        "<html><head></head><body>\n"
        f"<p><a href=\"https://marczewski.me.uk/easytype\">{family_name}</a> "
        f"is part of the neuro-inclusive EasyType suite. {summary} "
        "Every release ships with Regular, Italic, Bold, and Bold Italic so "
        "typographic systems can stay cohesive while respecting different "
        "reading needs.</p>\n"
        f"<p>{CONTRIBUTION_PARAGRAPH}</p>\n"
        "</body></html>\n"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for family_name, info in FAMILIES.items():
        folder = OUTPUT_DIR / info["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / "DESCRIPTION.en_us.html"
        dest.write_text(build_html(family_name, info["summary"]), encoding="utf-8")
        print(f"Wrote {dest}")


if __name__ == "__main__":
    main()

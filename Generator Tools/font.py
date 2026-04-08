#!/usr/bin/env python3
"""
EasyType Font Builder (multilingual final)
==========================================
Builds:
  • fonts/ttf/*.ttf  — hinted and platform-safe
  • fonts/web/*.woff2 — compressed for web

Supports:
  Latin + Latin-Extended + Greek + Cyrillic

Base font: Inter v4.1 (rsms/inter), downloaded from GitHub releases.
Inter's ss02 and cv05 disambiguation alternates are baked into
the default glyph set before EasyType modifications are applied.

Technical note:
  Existing cached Noto Sans files in base_fonts/ (NotoSans-*.ttf) can be
  deleted. Future builds download and extract Inter instead.

Requires:
  pip install fonttools requests
Optional:
  brew install woff2 ttfautohint
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import fractions
import json
import logging
import os
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from typing import Any

import requests
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)
log = logging.getLogger("easytype")

# ----------------------- Paths -----------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

INTER_RELEASE_URL = (
    "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
)
BASECACHE = os.path.join(REPO_ROOT, "base_fonts")
INTER_ZIP_CACHE = os.path.join(BASECACHE, "Inter-4.1.zip")
BASES = {
    "Regular": "Inter-Regular.ttf",
    "Italic": "Inter-Italic.ttf",
    "Bold": "Inter-Bold.ttf",
    "BoldItalic": "Inter-BoldItalic.ttf",
}
OUT_TTF = os.path.join(REPO_ROOT, "fonts", "ttf")
OUT_WEB = os.path.join(REPO_ROOT, "fonts", "web")
BUILD_REPORT_PATH = os.path.join(REPO_ROOT, "fonts", "build_report.json")
os.makedirs(BASECACHE, exist_ok=True)
os.makedirs(OUT_TTF, exist_ok=True)
os.makedirs(OUT_WEB, exist_ok=True)

VERSION_DISPLAY = "1.0.2"
VERSION_DECIMAL = "1.002"
VERSION_STR = f"EasyType v{VERSION_DISPLAY}"

# -------------------- Families -----------------------
FAMILY_DISPLAY = {
    "EasyType Sans": "Easy Type Sans",
    "EasyType Focus": "Easy Type Focus",
    "EasyType Steady": "Easy Type Steady",
}

STYLE_WEIGHTS = {
    "Regular": (400, "Regular"),
    "Italic": (400, "Italic"),
    "Bold": (700, "Bold"),
    "BoldItalic": (700, "Bold Italic"),
}


@dataclass
class FamilyConfig:
    anchor_strength: float
    xheight_factor: float
    letter_spacing: float
    word_spacing: float
    micro_level: float


FAMILIES = {
    "EasyType Sans": FamilyConfig(
        anchor_strength=0.25,
        xheight_factor=1.03,
        letter_spacing=1.06,
        word_spacing=1.12,
        micro_level=0.8,
    ),
    "EasyType Focus": FamilyConfig(
        anchor_strength=0.40,
        xheight_factor=1.06,
        letter_spacing=1.14,
        word_spacing=1.24,
        micro_level=1.0,
    ),
    "EasyType Steady": FamilyConfig(
        anchor_strength=0.55,
        xheight_factor=1.10,
        letter_spacing=1.22,
        word_spacing=1.32,
        micro_level=1.0,
    ),
}

FONT_PARAMS = {
    "entry_band": 0.18,
    "win_ascent_min": 1084,
    "win_descent_min": 427,
    "disambiguation_enabled": True,
    "base_cache_note": (
        "Legacy NotoSans-*.ttf cache files in base_fonts/ may be deleted. "
        "Future builds download Inter v4.1 from GitHub releases."
    ),
    "disambiguation": {
        "b_stem_shift": 12,
        "pq_descender_shift": 8,
        "l_foot_shift": 10,
    },
    "proportions": {
        "ascender_xheight_ratio": 1.2,
        "descender_xheight_ratio": 0.35,
    },
    "anchor_lc": {
        "a": 0.28,
        "b": 0.16,
        "c": 0.34,
        "d": 0.22,
        "e": 0.32,
        "f": 0.12,
        "g": 0.26,
        "h": 0.16,
        "i": 0.10,
        "j": 0.11,
        "k": 0.13,
        "l": 0.10,
        "m": 0.20,
        "n": 0.18,
        "o": 0.32,
        "p": 0.22,
        "q": 0.22,
        "r": 0.18,
        "s": 0.24,
        "t": 0.16,
        "u": 0.22,
        "v": 0.14,
        "w": 0.16,
        "x": 0.12,
        "y": 0.16,
        "z": 0.12,
    },
    "anchor_uc": {
        "A": 0.08,
        "B": 0.20,
        "C": 0.22,
        "D": 0.20,
        "E": 0.22,
        "F": 0.20,
        "G": 0.22,
        "H": 0.18,
        "I": 0.00,
        "J": 0.20,
        "K": 0.20,
        "L": 0.22,
        "M": 0.20,
        "N": 0.20,
        "O": 0.22,
        "P": 0.20,
        "Q": 0.22,
        "R": 0.20,
        "S": 0.22,
        "T": 0.18,
        "U": 0.20,
        "V": 0.16,
        "W": 0.18,
        "X": 0.14,
        "Y": 0.16,
        "Z": 0.14,
    },
    "micro_spacing_em": {
        "m": 0.010,
        "w": 0.009,
        "M": 0.012,
        "W": 0.012,
        "g": 0.008,
        "G": 0.010,
        "Q": 0.010,
        "8": 0.010,
        "0": 0.006,
        "n": 0.006,
        "h": 0.006,
        "u": 0.006,
        "r": 0.004,
        "p": 0.004,
        "q": 0.004,
        "o": -0.002,
        "O": -0.009,
        "i": -0.005,
        "l": -0.006,
        "I": -0.006,
        "1": -0.006,
        "|": -0.006,
        "t": -0.004,
        "f": -0.003,
        "j": -0.003,
        ":": -0.003,
        ";": -0.003,
    },
}

FAMILY_METRICS: dict[str, dict[str, dict[str, int]]] = {}

ANCHOR_BASE_MAP = {
    "Α": "A",
    "Β": "B",
    "Γ": "C",
    "Δ": "A",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Θ": "O",
    "Ι": "I",
    "Κ": "K",
    "Λ": "A",
    "Μ": "M",
    "Ν": "N",
    "Ξ": "E",
    "Ο": "O",
    "Π": "H",
    "Ρ": "P",
    "Σ": "S",
    "Τ": "T",
    "Υ": "Y",
    "Φ": "F",
    "Χ": "X",
    "Ψ": "Y",
    "Ω": "O",
    "α": "a",
    "β": "b",
    "γ": "c",
    "δ": "a",
    "ε": "e",
    "ζ": "z",
    "η": "h",
    "θ": "o",
    "ι": "i",
    "κ": "k",
    "λ": "a",
    "μ": "m",
    "ν": "n",
    "ξ": "e",
    "ο": "o",
    "π": "h",
    "ρ": "p",
    "σ": "s",
    "τ": "t",
    "υ": "u",
    "φ": "f",
    "χ": "x",
    "ψ": "y",
    "ω": "o",
    "А": "A",
    "В": "B",
    "С": "C",
    "Е": "E",
    "Н": "H",
    "К": "K",
    "М": "M",
    "О": "O",
    "Р": "P",
    "Т": "T",
    "У": "Y",
    "Х": "X",
    "а": "a",
    "в": "b",
    "е": "e",
    "к": "k",
    "м": "m",
    "н": "n",
    "о": "o",
    "р": "p",
    "с": "c",
    "т": "t",
    "у": "y",
    "х": "x",
}

def download_inter_zip() -> str:
    """Downloads the Inter release zip to BASECACHE if not already present. Returns the path to the zip file."""
    if not os.path.exists(INTER_ZIP_CACHE):
        log.info("Downloading Inter release zip...")
        r = requests.get(INTER_RELEASE_URL, stream=True)
        r.raise_for_status()
        with open(INTER_ZIP_CACHE, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        log.info("✓ Downloaded Inter zip to %s", INTER_ZIP_CACHE)
    else:
        log.info("✓ Found cached Inter zip")
    return INTER_ZIP_CACHE


def extract_base(style_filename: str) -> str:
    """Extracts a single static Inter TTF from the release zip into BASECACHE. Returns the local path to the extracted TTF.

    Inter 4.x stores static TTFs under a nested folder inside the zip.
    This function searches for the filename at any depth and extracts it.
    """
    dest = os.path.join(BASECACHE, style_filename)
    if os.path.exists(dest):
        log.info("✓ Found extracted base %s", style_filename)
        return dest

    zip_path = download_inter_zip()
    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        match = next(
            (
                entry
                for entry in zf.namelist()
                if entry.endswith(f"/{style_filename}") or entry == style_filename
            ),
            None,
        )
        if match is None:
            available = [entry for entry in zf.namelist() if entry.endswith(".ttf")]
            raise FileNotFoundError(
                f"Could not find {style_filename} in Inter zip. "
                f"Available TTFs: {available}"
            )
        with zf.open(match) as src, open(dest, "wb") as out:
            out.write(src.read())
    log.info("✓ Extracted %s → %s", style_filename, dest)
    return dest


def get_base_letter(ch: str) -> str:
    """Normalize diacritics to the base Latin letter when possible."""
    decomp = unicodedata.normalize("NFD", ch)
    for char in decomp:
        if char.isalpha():
            return char
    return ch


def set_coords(glyph: Any, coords: list[tuple[int, int]], end_pts: list[int], flags: list[int]) -> None:
    """Replace a glyph's coordinates while preserving contour metadata."""
    if len(coords) != len(flags):
        flags = list(flags) + [flags[-1]] * abs(len(coords) - len(flags))
    glyph.coordinates = GlyphCoordinates(coords)
    glyph.endPtsOfContours = end_pts
    glyph.flags = flags


def remove_soft_hyphen(tt: TTFont) -> None:
    """Remove the soft-hyphen cmap entry to avoid exposing a discretionary glyph."""
    cmap = tt.getBestCmap()
    if cmap and 0x00AD in cmap:
        glyph_name = cmap[0x00AD]
        log.info("✓ Removing soft-hyphen (U+00AD, glyph: %s)", glyph_name)
        for table in tt["cmap"].tables:
            if table.isUnicode() and 0x00AD in table.cmap:
                del table.cmap[0x00AD]


def apply_optical_anchor(tt: TTFont, entry_band: float, global_strength: float) -> None:
    """Shift entry-side points leftward to strengthen left-hand anchoring."""
    glyf = tt["glyf"]
    cmap = tt.getBestCmap() or {}
    affected = 0
    for code, glyph_name in cmap.items():
        ch = chr(code)
        if not (
            ("\u0000" <= ch <= "\u024F")
            or ("\u1E00" <= ch <= "\u1EFF")
            or ("\u0370" <= ch <= "\u03FF")
            or ("\u0400" <= ch <= "\u04FF")
        ):
            continue
        base = ANCHOR_BASE_MAP.get(ch, get_base_letter(ch))
        strength_key = FONT_PARAMS["anchor_lc"].get(base)
        if strength_key is None:
            strength_key = FONT_PARAMS["anchor_uc"].get(base)
        if not strength_key:
            continue
        glyph = glyf[glyph_name]
        if not hasattr(glyph, "getCoordinates"):
            continue
        coords, end_pts, flags = glyph.getCoordinates(glyf)
        if not coords:
            continue
        strength = strength_key * global_strength
        xs = [x for x, _ in coords]
        x_min = min(xs)
        x_max = max(xs)
        width = max(1, x_max - x_min)
        new_coords = []
        for x, y in coords:
            ratio = (x - x_min) / width
            if ratio <= entry_band:
                taper = 1.0 - (ratio / entry_band)
                new_coords.append((int(x - strength * taper * width), int(y)))
            else:
                new_coords.append((int(x), int(y)))
        set_coords(glyph, new_coords, list(end_pts), list(flags))
        affected += 1
    log.info("✓ Anchoring: %s glyphs (global=%.2f)", affected, global_strength)


def raise_xheight(tt: TTFont, factor: float) -> None:
    """Raise only the x-height zone and translate ascenders by the same absolute delta."""
    if abs(factor - 1.0) < 1e-3:
        return
    os2 = tt["OS/2"]
    xheight_y = int(getattr(os2, "sxHeight", 0))
    if xheight_y <= 0:
        raise ValueError("OS/2.sxHeight must be a positive value before raise_xheight runs.")
    baseline_y = 0
    new_xheight_y = int(round(xheight_y * factor))
    delta_y = new_xheight_y - xheight_y
    glyf = tt["glyf"]
    cmap = tt.getBestCmap() or {}
    for code, glyph_name in cmap.items():
        char = chr(code)
        if not char.islower():
            continue
        glyph = glyf[glyph_name]
        if not hasattr(glyph, "getCoordinates"):
            continue
        coords, end_pts, flags = glyph.getCoordinates(glyf)
        if not coords:
            continue
        updated_coords = []
        for x, y in coords:
            if baseline_y < y <= xheight_y:
                new_y = int(round(y * factor))
            elif y > xheight_y:
                new_y = y + delta_y
            else:
                new_y = y
            updated_coords.append((int(x), int(new_y)))
        set_coords(glyph, updated_coords, list(end_pts), list(flags))
    os2.sxHeight = new_xheight_y
    log.info("✓ x-height raised ×%.2f (x-height zone only)", factor)


def validate_proportions(tt: TTFont, family_name: str, style: str) -> None:
    """Validate x-height, ascender, and descender ratios after x-height changes."""
    os2 = tt["OS/2"]
    x_height = int(os2.sxHeight)
    ascender = int(os2.sTypoAscender)
    descender = abs(int(os2.sTypoDescender))
    min_ascender = x_height * FONT_PARAMS["proportions"]["ascender_xheight_ratio"]
    min_descender = x_height * FONT_PARAMS["proportions"]["descender_xheight_ratio"]
    if ascender < min_ascender:
        raise ValueError(
            f"Ascender/x-height ratio failed for {family_name} {style}: "
            f"asc={ascender}, xh={x_height}, desc={descender}, "
            f"required asc>={min_ascender:.2f}"
        )
    if descender < min_descender:
        raise ValueError(
            f"Descender/x-height ratio failed for {family_name} {style}: "
            f"asc={ascender}, xh={x_height}, desc={descender}, "
            f"required desc>={min_descender:.2f}"
        )
    log.info(
        "✓ Proportions OK [%s %s]: asc=%s, xh=%s, desc=%s",
        family_name,
        style,
        ascender,
        x_height,
        descender,
    )


def bake_disambiguation_defaults(
    tt: TTFont,
    feature_tags: frozenset[str] = frozenset({"ss02", "cv05"}),
) -> None:
    """Promotes Inter's disambiguation alternate glyphs to default glyph positions by copying their outlines and metrics over the ambiguous base glyphs.

    Inter's ss02 stylistic set contains professionally drawn alternate
    forms for commonly confused characters (I with serifs, l with foot
    curve, disambiguated digits). cv05 provides a lowercase l with tail.

    Rather than activating these as CSS features (which requires
    font-feature-settings), this function bakes the alternates into the
    default slots so every user receives them without configuration.

    Args:
        tt: Open TTFont object (modified in place).
        feature_tags: GSUB feature tags whose SingleSubst mappings to
            promote. Defaults to ss02 and cv05.
    """
    if not FONT_PARAMS["disambiguation_enabled"]:
        return

    gsub = tt.get("GSUB")
    if not gsub:
        log.warning("No GSUB table found — skipping disambiguation baking")
        return

    table = gsub.table
    if not table.FeatureList or not table.LookupList:
        log.warning("GSUB FeatureList or LookupList missing")
        return

    target_lookups: set[int] = set()
    for feat_record in table.FeatureList.FeatureRecord:
        if feat_record.FeatureTag in feature_tags:
            target_lookups.update(feat_record.Feature.LookupListIndex)

    if not target_lookups:
        log.warning(
            "No GSUB lookups found for features %s. Check that Inter's GSUB table contains ss02/cv05.",
            feature_tags,
        )
        return

    substitutions: dict[str, str] = {}
    for idx in sorted(target_lookups):
        lookup = table.LookupList.Lookup[idx]
        for subtable in lookup.SubTable:
            if hasattr(subtable, "mapping"):
                substitutions.update(subtable.mapping)

    if not substitutions:
        log.warning("GSUB lookups found but contained no SingleSubst mappings")
        return

    glyf_table = tt["glyf"]
    hmtx = tt["hmtx"].metrics
    baked = 0
    skipped = 0

    for default_name, alternate_name in substitutions.items():
        if default_name not in glyf_table:
            log.warning("  SKIP %s: not in glyf table", default_name)
            skipped += 1
            continue
        if alternate_name not in glyf_table:
            log.warning(
                "  SKIP %s → %s: alternate not in glyf table",
                default_name,
                alternate_name,
            )
            skipped += 1
            continue

        alt_glyph = glyf_table[alternate_name]
        default_glyph = glyf_table[default_name]

        default_glyph.numberOfContours = alt_glyph.numberOfContours
        if alt_glyph.numberOfContours >= 0:
            coords, end_pts, flags = alt_glyph.getCoordinates(glyf_table)
            default_glyph.coordinates = GlyphCoordinates(coords)
            default_glyph.endPtsOfContours = list(end_pts)
            default_glyph.flags = list(flags)
            if hasattr(default_glyph, "components"):
                default_glyph.components = []
            if hasattr(alt_glyph, "program") and alt_glyph.program is not None:
                default_glyph.program = alt_glyph.program
            else:
                from fontTools.ttLib.tables.ttProgram import Program

                default_glyph.program = Program()
        elif alt_glyph.isComposite():
            default_glyph.components = list(alt_glyph.components)
            if hasattr(default_glyph, "coordinates"):
                del default_glyph.coordinates
            if hasattr(default_glyph, "endPtsOfContours"):
                del default_glyph.endPtsOfContours
            if hasattr(default_glyph, "flags"):
                del default_glyph.flags
            if hasattr(alt_glyph, "program") and alt_glyph.program is not None:
                default_glyph.program = alt_glyph.program
            elif hasattr(default_glyph, "program"):
                del default_glyph.program

        if alternate_name in hmtx and default_name in hmtx:
            alt_adv, _ = hmtx[alternate_name]
            _, default_lsb = hmtx[default_name]
            hmtx[default_name] = (alt_adv, default_lsb)

        log.info("  ✓ Baked: %s ← %s", default_name, alternate_name)
        baked += 1

    log.info(
        "✓ Disambiguation baking complete: %s glyphs promoted, %s skipped",
        baked,
        skipped,
    )


def verify_inter_gsub(tt: TTFont) -> None:
    """Checks that the loaded Inter TTF contains the expected GSUB disambiguation features. Logs a summary of what was found.
    Raises RuntimeError if ss02 is completely absent.
    """
    gsub = tt.get("GSUB")
    if not gsub or not gsub.table.FeatureList:
        raise RuntimeError(
            "Loaded base font has no GSUB table. "
            "This does not appear to be Inter. "
            "Check that the correct TTF was downloaded."
        )
    found_tags = {
        fr.FeatureTag
        for fr in gsub.table.FeatureList.FeatureRecord
    }
    for tag in ("ss02", "cv05"):
        if tag in found_tags:
            log.info("✓ GSUB feature '%s' confirmed present", tag)
        else:
            log.warning(
                "GSUB feature '%s' not found in base font. "
                "Disambiguation baking for this feature will be skipped.",
                tag,
            )
    if "ss02" not in found_tags:
        raise RuntimeError(
            "ss02 disambiguation feature not found in base font. "
            "Inter v4.0+ is required. "
            f"Found features: {sorted(found_tags)}"
        )


def apply_comfort_spacing(tt: TTFont, letter_factor: float, word_factor: float) -> None:
    """Scale advance widths for non-space glyphs and the space glyph separately."""
    hmtx = tt["hmtx"].metrics
    for glyph_name, (advance, lsb) in list(hmtx.items()):
        if glyph_name == "space":
            continue
        hmtx[glyph_name] = (max(1, int(round(advance * letter_factor))), lsb)
    if "space" in hmtx:
        advance, lsb = hmtx["space"]
        hmtx["space"] = (max(1, int(round(advance * word_factor))), lsb)
    log.info("✓ Spacing: letters×%.2f, words×%.2f", letter_factor, word_factor)


def apply_micro_spacing(tt: TTFont, level: float) -> None:
    """Apply character-specific micro spacing adjustments to advance widths."""
    if level <= 0:
        return
    upm = tt["head"].unitsPerEm
    cmap = tt.getBestCmap() or {}
    hmtx = tt["hmtx"].metrics
    count = 0
    for code, glyph_name in cmap.items():
        char = chr(code)
        base = get_base_letter(char)
        key = FONT_PARAMS["micro_spacing_em"].get(char)
        if key is None:
            key = FONT_PARAMS["micro_spacing_em"].get(base)
        if not key:
            continue
        delta_units = int(round(key * level * upm))
        if glyph_name in hmtx:
            advance, lsb = hmtx[glyph_name]
            hmtx[glyph_name] = (max(1, advance + delta_units), lsb)
            count += 1
    log.info("✓ Micro-spacing applied to %s glyphs", count)


def set_naming(
    tt: TTFont,
    family: str,
    style_key: str,
    style_label: str,
    weight: int,
) -> None:
    """Set Google Fonts-compatible naming records and style metadata."""
    names = tt["name"]
    family_label = FAMILY_DISPLAY.get(family, family)
    full_name = f"{family_label} {style_label}"
    postscript_name = f"{family.replace(' ', '')}-{style_key}"

    def set_name(name_id: int, value: str) -> None:
        names.setName(value, name_id, 3, 1, 0x409)

    names.names = [name for name in names.names if name.nameID not in [1, 2, 4, 5, 6, 16]]
    set_name(1, family_label)
    names.removeNames(nameID=16)
    set_name(2, style_label)
    set_name(4, full_name)
    set_name(5, f"Version {VERSION_DECIMAL}")
    set_name(6, postscript_name)

    if "OS/2" in tt:
        os2 = tt["OS/2"]
        os2.usWeightClass = weight
        selection = 0
        if "Regular" in style_label:
            selection |= 1 << 6
        if "Bold" in style_label:
            selection |= 1 << 5
        if "Italic" in style_label:
            selection |= 1 << 0
        os2.fsSelection &= ~((1 << 0) | (1 << 5) | (1 << 6))
        os2.fsSelection |= selection
        os2.fsSelection |= 1 << 7

    if "head" in tt:
        tt["head"].fontRevision = float(fractions.Fraction(VERSION_DECIMAL))
    log.info("✓ Set naming for %s", postscript_name)


def ensure_win_metrics(tt: TTFont) -> None:
    """Clamp Windows ascent/descent metrics to safe minimums."""
    head = tt["head"]
    os2 = tt["OS/2"]
    if os2.usWinAscent < head.yMax:
        os2.usWinAscent = max(head.yMax, FONT_PARAMS["win_ascent_min"])
    else:
        os2.usWinAscent = max(os2.usWinAscent, FONT_PARAMS["win_ascent_min"])
    descent = abs(head.yMin)
    if os2.usWinDescent < descent:
        os2.usWinDescent = max(descent, FONT_PARAMS["win_descent_min"])
    else:
        os2.usWinDescent = max(os2.usWinDescent, FONT_PARAMS["win_descent_min"])


def ensure_minus_glyph(tt: TTFont) -> None:
    """Clone an existing hyphen-like glyph to U+2212 when missing."""
    cmap = tt.getBestCmap() or {}
    if 0x2212 in cmap:
        return
    glyph_order = list(tt.getGlyphOrder())
    src_name = None
    for candidate in ("minus", "uni2212", "hyphen", "uni2010"):
        if candidate in glyph_order:
            src_name = candidate
            break
    if not src_name:
        return
    glyf = tt["glyf"]
    source_glyph = glyf[src_name]
    new_glyph = source_glyph.__class__()
    new_glyph.numberOfContours = source_glyph.numberOfContours
    if source_glyph.numberOfContours >= 0:
        coords, end_pts, flags = source_glyph.getCoordinates(glyf)
        new_glyph.coordinates = GlyphCoordinates(coords)
        new_glyph.endPtsOfContours = list(end_pts)
        new_glyph.flags = list(flags)
        if hasattr(source_glyph, "program") and source_glyph.program is not None:
            new_glyph.program = source_glyph.program
        else:
            from fontTools.ttLib.tables.ttProgram import Program

            new_glyph.program = Program()
    else:
        new_glyph.components = list(source_glyph.components)
    if hasattr(source_glyph, "program") and getattr(new_glyph, "program", None) is None:
        new_glyph.program = source_glyph.program
    glyf["uni2212"] = new_glyph
    if "uni2212" not in glyph_order:
        glyph_order.append("uni2212")
        tt.setGlyphOrder(glyph_order)
    hmtx = tt["hmtx"].metrics
    if src_name in hmtx:
        hmtx["uni2212"] = hmtx[src_name]
    for table in tt["cmap"].tables:
        if table.isUnicode():
            table.cmap[0x2212] = "uni2212"


def sync_space_nbspace(tt: TTFont) -> None:
    """Keep non-breaking space width aligned to the regular space width."""
    hmtx = tt["hmtx"].metrics
    if "space" not in hmtx:
        return
    advance, lsb = hmtx["space"]
    for name in ("nbspace", "nonbreakingspace", "uni00A0"):
        if name in hmtx:
            hmtx[name] = (advance, lsb)


def sanitize_gdef_marks(tt: TTFont) -> None:
    """Downgrade spacing-mark glyph classes that would trigger FontBakery warnings."""
    if "GDEF" not in tt:
        return
    gdef = tt["GDEF"].table
    glyph_class = getattr(gdef, "GlyphClassDef", None)
    if not glyph_class or not glyph_class.classDefs:
        return
    hmtx = tt["hmtx"].metrics
    for glyph_name, glyph_class_id in list(glyph_class.classDefs.items()):
        if glyph_class_id == 3 and glyph_name in hmtx and hmtx[glyph_name][0] != 0:
            glyph_class.classDefs[glyph_name] = 1


def sanitize_stat_table(tt: TTFont) -> None:
    """Drop duplicate STAT axis values that upset Google Fonts checks."""
    stat = tt.get("STAT")
    if not stat:
        return
    table = stat.table
    axis_values = table.AxisValueArray.AxisValue
    seen = set()
    filtered = []
    for value in axis_values:
        axis_index = getattr(value, "AxisIndex", None)
        if axis_index is None or axis_index not in seen:
            filtered.append(value)
            if axis_index is not None:
                seen.add(axis_index)
    if len(filtered) == len(axis_values):
        return
    table.AxisValueArray.AxisValue = filtered
    table.AxisValueCount = len(filtered)
    setattr(table.AxisValueArray, "AxisValueCount", len(filtered))
    log.info(
        "✓ STAT table reduced to %s axis values (removed %s)",
        len(filtered),
        len(axis_values) - len(filtered),
    )


def clone_glyph(tt: TTFont, src_name: str, dst_name: str, target_code: int) -> None:
    """Clone a glyph outline and cmap mapping to a new Unicode target."""
    glyf = tt["glyf"]
    hmtx = tt["hmtx"].metrics
    glyph_order = list(tt.getGlyphOrder())
    if dst_name in glyf or src_name not in glyf:
        return
    src = glyf[src_name]
    new_glyph = src.__class__()
    new_glyph.numberOfContours = src.numberOfContours
    if src.numberOfContours >= 0:
        coords, end_pts, flags = src.getCoordinates(tt["glyf"])
        new_glyph.coordinates = GlyphCoordinates(coords)
        new_glyph.endPtsOfContours = list(end_pts)
        new_glyph.flags = list(flags)
        if hasattr(src, "program") and src.program is not None:
            new_glyph.program = src.program
        else:
            from fontTools.ttLib.tables.ttProgram import Program

            new_glyph.program = Program()
    else:
        new_glyph.components = list(src.components)
        if hasattr(src, "program"):
            new_glyph.program = src.program
    glyf[dst_name] = new_glyph
    glyph_order.append(dst_name)
    tt.setGlyphOrder(glyph_order)
    if src_name in hmtx:
        hmtx[dst_name] = hmtx[src_name]
    for table in tt["cmap"].tables:
        if table.isUnicode():
            table.cmap[target_code] = dst_name


def ensure_case_pairs(tt: TTFont) -> None:
    """Clone missing uppercase/lowercase singleton pairs for cmap completeness."""
    cmap = tt.getBestCmap() or {}
    for codepoint, glyph_name in list(cmap.items()):
        char = chr(codepoint)
        upper_str = unicodedata.normalize("NFC", char).upper()
        lower_str = unicodedata.normalize("NFC", char).lower()
        if len(upper_str) != 1 or len(lower_str) != 1:
            continue
        upper = ord(upper_str)
        lower = ord(lower_str)
        for target in (upper, lower):
            if target == codepoint:
                continue
            if target not in cmap:
                dst_name = f"uni{target:04X}"
                clone_glyph(tt, glyph_name, dst_name, target)


IDENTITY_TRANSFORM = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _compose_transforms(
    parent: tuple[float, float, float, float, float, float],
    child: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    """Compose affine transform tuples used by composite glyph flattening."""
    a1, b1, c1, d1, e1, f1 = parent
    a2, b2, c2, d2, e2, f2 = child
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 + a1 * e2 + b1 * f2,
        f1 + c1 * e2 + d1 * f2,
    )


def _draw_as_contours(
    tt: TTFont,
    glyph_name: str,
    pen: TTGlyphPen,
    transform: tuple[float, float, float, float, float, float] = IDENTITY_TRANSFORM,
) -> None:
    """Draw composite glyphs as simple contours into a TrueType glyph pen."""
    glyph = tt["glyf"][glyph_name]
    if glyph.isComposite():
        for component in glyph.components:
            comp_name, comp_transform = component.getComponentInfo()
            nested_transform = _compose_transforms(transform, comp_transform)
            _draw_as_contours(tt, comp_name, pen, nested_transform)
        return
    used_pen = pen if transform == IDENTITY_TRANSFORM else TransformPen(pen, transform)
    glyph.draw(used_pen, tt["glyf"])


def flatten_composites(tt: TTFont) -> None:
    """Replace composite glyphs with simple contours before final save."""
    glyf_table = tt["glyf"]
    for glyph_name in tt.getGlyphOrder():
        glyph = glyf_table[glyph_name]
        if not glyph.isComposite():
            continue
        pen = TTGlyphPen(glyf_table)
        _draw_as_contours(tt, glyph_name, pen)
        new_glyph = pen.glyph()
        if hasattr(glyph, "program") and glyph.program is not None:
            new_glyph.program = glyph.program
        else:
            from fontTools.ttLib.tables.ttProgram import Program

            new_glyph.program = Program()
        glyf_table[glyph_name] = new_glyph


def capture_metrics_snapshot(tt: TTFont) -> dict[str, dict[str, int]]:
    """Capture a family's regular-style vertical metrics for reuse."""
    snapshot: dict[str, dict[str, int]] = {}
    if "hhea" in tt:
        hhea = tt["hhea"]
        snapshot["hhea"] = {
            "ascent": hhea.ascent,
            "descent": hhea.descent,
            "lineGap": hhea.lineGap,
        }
    if "OS/2" in tt:
        os2 = tt["OS/2"]
        snapshot["OS/2"] = {
            "sTypoAscender": os2.sTypoAscender,
            "sTypoDescender": os2.sTypoDescender,
            "sTypoLineGap": os2.sTypoLineGap,
            "usWinAscent": os2.usWinAscent,
            "usWinDescent": os2.usWinDescent,
        }
    return snapshot


def apply_metrics_snapshot(tt: TTFont, family: str) -> None:
    """Apply cached family metrics captured from the regular build."""
    snapshot = FAMILY_METRICS.get(family)
    if not snapshot:
        return
    if "hhea" in tt and "hhea" in snapshot:
        hhea = tt["hhea"]
        data = snapshot["hhea"]
        hhea.ascent = data["ascent"]
        hhea.descent = data["descent"]
        hhea.lineGap = data["lineGap"]
    if "OS/2" in tt and "OS/2" in snapshot:
        os2 = tt["OS/2"]
        data = snapshot["OS/2"]
        os2.sTypoAscender = data["sTypoAscender"]
        os2.sTypoDescender = data["sTypoDescender"]
        os2.sTypoLineGap = data["sTypoLineGap"]
        os2.usWinAscent = data["usWinAscent"]
        os2.usWinDescent = data["usWinDescent"]


def recompute_xavg(tt: TTFont) -> None:
    """Recompute OS/2.xAvgCharWidth from current advance widths."""
    os2 = tt["OS/2"]
    metrics = tt["hmtx"].metrics
    total = 0
    count = 0
    for advance, _ in metrics.values():
        if advance > 0:
            total += advance
            count += 1
    if count == 0:
        return
    os2.xAvgCharWidth = int(round(total / count))


def set_head_flags(tt: TTFont) -> None:
    """Enable the force-ppem-to-integer head flag used in prior builds."""
    tt["head"].flags |= 1 << 3


def post_hint_fixup(font_path: str) -> None:
    """Apply final metric fixups after hinting or direct save."""
    tt = TTFont(font_path)
    ensure_win_metrics(tt)
    recompute_xavg(tt)
    set_head_flags(tt)
    tt.save(font_path)


def read_font_report(font_path: str, cfg: FamilyConfig) -> dict[str, Any]:
    """Read a saved font file and extract build-report metrics for one style."""
    tt = TTFont(font_path)
    os2 = tt["OS/2"]
    return {
        "glyph_count": len(tt.getGlyphOrder()),
        "os2": {
            "xHeight": int(os2.sxHeight),
            "ascender": int(os2.sTypoAscender),
            "descender": int(os2.sTypoDescender),
        },
        "params": {
            "anchor_strength": cfg.anchor_strength,
            "xheight_factor": cfg.xheight_factor,
            "letter_spacing": cfg.letter_spacing,
            "word_spacing": cfg.word_spacing,
        },
    }


def auto_hint(in_path: str, out_path: str, enabled: bool = True) -> bool:
    """Run ttfautohint when available and not explicitly disabled."""
    if not enabled:
        log.info("→ Hinting disabled by --no-hint for %s", os.path.basename(out_path))
        return False
    bin_path = shutil.which("ttfautohint")
    if not bin_path:
        log.warning("ttfautohint not found; skipping hinting")
        return False
    result = subprocess.run(
        [bin_path, "--windows-compatibility", "--symbol", "--no-info", in_path, out_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        log.warning("ttfautohint failed: %s", result.stderr.strip())
        return False
    log.info("✓ Hinting applied → %s", out_path)
    return True


def build_one(
    src_path: str,
    out_path: str,
    family: str,
    style_key: str,
    style_label: str,
    weight: int,
    cfg: FamilyConfig,
    hinting_enabled: bool = True,
) -> dict[str, Any]:
    """Build one font style, save it, and return its build-report metrics."""
    tt = TTFont(src_path)

    bake_disambiguation_defaults(tt)
    apply_optical_anchor(tt, FONT_PARAMS["entry_band"], cfg.anchor_strength)
    raise_xheight(tt, cfg.xheight_factor)
    apply_comfort_spacing(tt, cfg.letter_spacing, cfg.word_spacing)
    apply_micro_spacing(tt, cfg.micro_level)

    set_naming(tt, family, style_key, style_label, weight)
    ensure_minus_glyph(tt)
    remove_soft_hyphen(tt)
    sync_space_nbspace(tt)
    ensure_case_pairs(tt)

    flatten_composites(tt)

    sanitize_gdef_marks(tt)
    sanitize_stat_table(tt)

    if FAMILY_METRICS.get(family):
        apply_metrics_snapshot(tt, family)
    validate_proportions(tt, family, style_label)

    tmp = out_path.replace(".ttf", "-tmp.ttf")
    tt.save(tmp)
    if not auto_hint(tmp, out_path, enabled=hinting_enabled):
        shutil.move(tmp, out_path)
    else:
        os.remove(tmp)

    post_hint_fixup(out_path)
    log.info("→ Saved %s", out_path)
    return read_font_report(out_path, cfg)


def read_font_report_from_tt(tt: TTFont) -> dict[str, Any]:
    """Extract report metrics from an in-memory TTFont for dry-run output."""
    os2 = tt["OS/2"]
    return {
        "glyph_count": len(tt.getGlyphOrder()),
        "os2": {
            "xHeight": int(os2.sxHeight),
            "ascender": int(os2.sTypoAscender),
            "descender": int(os2.sTypoDescender),
        },
        "params": {},
    }


def simulate_build(
    src_path: str,
    family: str,
    style_label: str,
    cfg: FamilyConfig,
    out_path: str,
) -> None:
    """Run the non-destructive transform/validation path for a dry run."""
    tt = TTFont(src_path)
    bake_disambiguation_defaults(tt)
    apply_optical_anchor(tt, FONT_PARAMS["entry_band"], cfg.anchor_strength)
    raise_xheight(tt, cfg.xheight_factor)
    validate_proportions(tt, family, style_label)
    preview = copy.deepcopy(read_font_report_from_tt(tt))
    preview["params"]["letter_spacing"] = cfg.letter_spacing
    preview["params"]["word_spacing"] = cfg.word_spacing
    preview["params"]["anchor_strength"] = cfg.anchor_strength
    preview["params"]["xheight_factor"] = cfg.xheight_factor
    log.info("→ Dry run would build %s with %s glyphs", out_path, preview["glyph_count"])


def compress_to_woff2(ttf_path: str) -> None:
    """Compress a generated TTF into WOFF2 when the encoder is available."""
    possible_paths = [
        os.environ.get("WOFF2_BIN"),
        shutil.which("woff2_compress"),
        "/opt/homebrew/bin/woff2_compress",
        "/usr/local/bin/woff2_compress",
    ]
    woff2_bin = next((path for path in possible_paths if path and os.path.exists(path)), None)
    if not woff2_bin:
        log.warning("woff2_compress not found; skipping webfont")
        return

    ttf_dir = os.path.dirname(ttf_path)
    ttf_base = os.path.basename(ttf_path)
    out_woff = os.path.join(OUT_WEB, ttf_base.replace(".ttf", ".woff2"))
    os.makedirs(os.path.dirname(out_woff), exist_ok=True)
    generated_woff_path = os.path.join(ttf_dir, ttf_base.replace(".ttf", ".woff2"))

    log.info("Processing %s → %s", ttf_base, out_woff)
    try:
        subprocess.run(
            [woff2_bin, ttf_base],
            cwd=ttf_dir,
            check=True,
            capture_output=True,
        )
        shutil.move(generated_woff_path, out_woff)
        log.info("✓ Webfont: %s", out_woff)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else str(exc.stderr)
        log.warning("woff2_compress failed on %s: %s", ttf_base, stderr)
    except FileNotFoundError:
        log.warning("Could not locate generated .woff2 output for %s", ttf_base)


def resolve_family_filter(family_name: str | None) -> dict[str, FamilyConfig]:
    """Return all families or the single case-insensitive match requested by CLI."""
    if not family_name:
        return FAMILIES
    wanted = family_name.casefold()
    for name, cfg in FAMILIES.items():
        if name.casefold() == wanted:
            return {name: cfg}
    raise ValueError(f"Unknown family: {family_name}")


def get_git_commit() -> str:
    """Return the current short git commit hash or 'unknown' when unavailable."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def write_build_report(report: dict[str, Any]) -> None:
    """Write the structured build report JSON to fonts/build_report.json."""
    os.makedirs(os.path.dirname(BUILD_REPORT_PATH), exist_ok=True)
    with open(BUILD_REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    """Parse command-line options for filtered, dry-run, or no-hint builds."""
    parser = argparse.ArgumentParser(description="Build the EasyType font family.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run outline transforms and validation without writing output files.",
    )
    parser.add_argument(
        "--family",
        help='Build only one family, e.g. --family "EasyType Steady".',
    )
    parser.add_argument(
        "--no-hint",
        action="store_true",
        help="Skip ttfautohint even if it is installed.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION_STR,
    )
    return parser.parse_args()


def main() -> int:
    """Build all requested EasyType font families or run a dry-run validation pass."""
    args = parse_args()
    selected_families = resolve_family_filter(args.family)
    base_paths = {style: extract_base(filename) for style, filename in BASES.items()}

    # Verify the downloaded Inter has the expected GSUB features
    verify_inter_gsub(TTFont(base_paths["Regular"]))

    report = {
        "version": VERSION_DISPLAY,
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "families": {},
    }

    for family, cfg in selected_families.items():
        log.info("=== Building %s ===", family)
        if args.dry_run:
            for style, (_, style_label) in STYLE_WEIGHTS.items():
                src = base_paths[style]
                out_ttf = os.path.join(OUT_TTF, f"{family.replace(' ', '')}-{style}.ttf")
                simulate_build(src, family, style_label, cfg, out_ttf)
            continue

        family_report: dict[str, Any] = {}
        for style, (weight, style_label) in STYLE_WEIGHTS.items():
            src = base_paths[style]
            out_ttf = os.path.join(OUT_TTF, f"{family.replace(' ', '')}-{style}.ttf")
            style_report = build_one(
                src,
                out_ttf,
                family,
                style,
                style_label,
                weight,
                cfg,
                hinting_enabled=not args.no_hint,
            )
            family_report[style] = style_report
            if style_label.lower() == "regular":
                FAMILY_METRICS[family] = capture_metrics_snapshot(TTFont(out_ttf))
            compress_to_woff2(out_ttf)
        report["families"][family] = family_report

    if args.dry_run:
        log.info("✓ Dry run complete: no files were written")
        return 0

    write_build_report(report)
    log.info("✓ Build report written to %s", BUILD_REPORT_PATH)
    log.info("✅ Done: hinted TTFs in fonts/ttf, WOFF2 in fonts/web")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

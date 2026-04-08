#!/usr/bin/env python3
"""
EasyType Font Builder
=====================
Builds:
  • fonts/ttf/*.ttf   — hinted, platform-safe TrueType
  • fonts/web/*.woff2 — compressed webfonts

Supports:
  Latin + Latin-Extended + Greek + Cyrillic

Base font: Inter v4.1 (rsms/inter), downloaded from GitHub releases.
Inter's ss02 and cv05 disambiguation alternates are baked into the
default glyph set before EasyType modifications are applied.

Requires:
  pip install fonttools requests
Optional:
  brew install woff2 ttfautohint

Usage:
  python3 font.py                          # build all families
  python3 font.py --family "EasyType Sans" # one family only
  python3 font.py --dry-run               # validate, no output
  python3 font.py --no-hint               # skip ttfautohint
  python3 font.py --version
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import enum
import fractions
import json
import logging
import os
import shutil
import subprocess
import unicodedata
import zipfile
from dataclasses import dataclass
from typing import Any

import requests
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("easytype")

# ─── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR        = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT         = os.path.dirname(SCRIPT_DIR)
BASECACHE         = os.path.join(REPO_ROOT, "base_fonts")
OUT_TTF           = os.path.join(REPO_ROOT, "fonts", "ttf")
OUT_WEB           = os.path.join(REPO_ROOT, "fonts", "web")
BUILD_REPORT_PATH = os.path.join(REPO_ROOT, "fonts", "build_report.json")

for _d in (BASECACHE, OUT_TTF, OUT_WEB):
    os.makedirs(_d, exist_ok=True)

# ─── Inter source ─────────────────────────────────────────────────────────────

INTER_RELEASE_URL = (
    "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
)
INTER_ZIP_CACHE = os.path.join(BASECACHE, "Inter-4.1.zip")
BASES = {
    "Regular":    "Inter-Regular.ttf",
    "Italic":     "Inter-Italic.ttf",
    "Bold":       "Inter-Bold.ttf",
    "BoldItalic": "Inter-BoldItalic.ttf",
}

# ─── Version ──────────────────────────────────────────────────────────────────

VERSION_DISPLAY = "1.1.0"
VERSION_DECIMAL = "1.100"
VERSION_STR     = f"EasyType v{VERSION_DISPLAY}"

# ─── Families ─────────────────────────────────────────────────────────────────

FAMILY_DISPLAY = {
    "EasyType Sans":   "Easy Type Sans",
    "EasyType Focus":  "Easy Type Focus",
    "EasyType Steady": "Easy Type Steady",
}

STYLE_WEIGHTS = {
    "Regular":    (400, "Regular"),
    "Italic":     (400, "Italic"),
    "Bold":       (700, "Bold"),
    "BoldItalic": (700, "Bold Italic"),
}

@dataclass
class FamilyConfig:
    anchor_strength: float
    xheight_factor:  float
    letter_spacing:  float
    word_spacing:    float
    micro_level:     float

FAMILIES: dict[str, FamilyConfig] = {
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

# ─── Tuning parameters ────────────────────────────────────────────────────────

FONT_PARAMS: dict[str, Any] = {
    # Optical anchoring — fraction of glyph width treated as entry zone
    "entry_band": 0.18,

    # Platform metric safety floors (units)
    "win_ascent_min":  1084,
    "win_descent_min": 427,

    # Proportion guard — minimum ratios post x-height scaling
    "proportions": {
        "ascender_xheight_ratio":  1.2,
        "descender_xheight_ratio": 0.35,
    },

    # Stem disambiguation — shift the extreme terminus point outward.
    # No new points are added; the adjacent Bezier handles naturally
    # curve to create the shoulder. shoulder_width is UPM-relative.
    "stem_shift": {
        "enabled":                True,
        "shoulder_width":         0.04,  # q — stem tip is relatively open
        "shoulder_width_reduced": 0.03,  # b, p — bowl junction adds apparent mass
        "y_tolerance":            0.05,
    },

    # Per-glyph anchor strengths — lowercase
    "anchor_lc": {
        "a":0.28,"b":0.16,"c":0.34,"d":0.22,"e":0.32,"f":0.22,
        "g":0.26,"h":0.16,"i":0.16,"j":0.16,"k":0.18,"l":0.14,
        "m":0.20,"n":0.18,"o":0.32,"p":0.22,"q":0.22,"r":0.22,
        "s":0.24,"t":0.20,"u":0.22,"v":0.14,"w":0.16,"x":0.16,
        "y":0.16,"z":0.16,
    },
    # Per-glyph anchor strengths — uppercase
    "anchor_uc": {
        "A":0.08,"B":0.20,"C":0.22,"D":0.20,"E":0.22,"F":0.20,
        "G":0.22,"H":0.18,"I":0.00,"J":0.20,"K":0.20,"L":0.22,
        "M":0.20,"N":0.20,"O":0.22,"P":0.20,"Q":0.22,"R":0.20,
        "S":0.22,"T":0.22,"U":0.20,"V":0.16,"W":0.18,"X":0.16,
        "Y":0.16,"Z":0.14,
    },
    # Per-glyph advance-width micro-tuning (UPM-relative, signed)
    "micro_spacing_em": {
        "m":+0.010,"w":+0.009,"M":+0.012,"W":+0.012,
        "g":+0.008,"G":+0.010,"Q":+0.010,"8":+0.010,"0":+0.006,
        "n":+0.006,"h":+0.006,"u":+0.006,"r":+0.004,
        "p":+0.004,"q":+0.004,"o":-0.002,"O":-0.009,
        "i":-0.005,"l":-0.006,"I":-0.006,"1":-0.006,
        "|":-0.006,"t":-0.004,"f":-0.003,"j":-0.003,
        ":":-0.003,";":-0.003,
    },
}

# ─── Stem-shift disambiguation map ───────────────────────────────────────────

class StemPosition(enum.Enum):
    """Which extreme point to shift for stem disambiguation.

    top_left    = leftmost  point near y_max (b-type entry)
    top_right   = rightmost point near y_max
    bottom_left = leftmost  point near y_min (p-type descender)
    bottom_right= rightmost point near y_min (q-type descender)
    """
    top_left     = "top_left"
    top_right    = "top_right"
    bottom_left  = "bottom_left"
    bottom_right = "bottom_right"

# Declarative: codepoint → which extreme point to shift.
# Add codepoints here to extend to new scripts — no other code changes needed.

_TL = StemPosition.top_left
_TR = StemPosition.top_right
_BL = StemPosition.bottom_left
_BR = StemPosition.bottom_right

STEM_SHIFT_MAP: dict[int, StemPosition] = {
    0x0062: _TL,  # b  Latin
    0x0064: _TR,  # d  Latin
    0x0431: _TL,  # б  Cyrillic be
    0x0411: _TL,  # Б  Cyrillic Be
    0x03B2: _TL,  # β  Greek beta
    0x00FE: _TL,  # þ  Latin thorn
    0x044C: _TL,  # ь  Cyrillic soft sign
    0x044A: _TL,  # ъ  Cyrillic hard sign
    0x042A: _TL,  # Ъ  Cyrillic Hard Sign
    0x042C: _TL,  # Ь  Cyrillic Soft Sign
    0x0070: _BL,  # p  Latin
    0x0440: _BL,  # р  Cyrillic er
    0x0420: _BL,  # Р  Cyrillic Er
    0x03C1: _BL,  # ρ  Greek rho
    0x0071: _BR,  # q  Latin
    # These share identical stem geometry with their base forms
    0x0253: _TL,  # ɓ  Latin small b with hook (IPA/African)
    0x0180: _TL,  # ƀ  Latin small b with stroke
    0x018C: _TL,  # ƌ  Latin small d with topbar (mirror of b-form)
    0x01A5: _BL,  # ƥ  Latin small p with hook
    0x02A0: _BR,  # ʠ  Latin small q with hook
    0x0036: _TR,  # 6  top curves right, distinguishes from 9
    0x0039: _BL,  # 9  bottom curves left, distinguishes from 6
}

# ─── Greek + Cyrillic → Latin anchor analogues ────────────────────────────────

ANCHOR_BASE_MAP: dict[str, str] = {
    "Α":"A","Β":"B","Γ":"C","Δ":"A","Ε":"E","Ζ":"Z","Η":"H","Θ":"O",
    "Ι":"I","Κ":"K","Λ":"A","Μ":"M","Ν":"N","Ξ":"E","Ο":"O","Π":"H",
    "Ρ":"P","Σ":"S","Τ":"T","Υ":"Y","Φ":"F","Χ":"X","Ψ":"Y","Ω":"O",
    "α":"a","β":"b","γ":"c","δ":"a","ε":"e","ζ":"z","η":"h","θ":"o",
    "ι":"i","κ":"k","λ":"a","μ":"m","ν":"n","ξ":"e","ο":"o","π":"h",
    "ρ":"p","σ":"s","τ":"t","υ":"u","φ":"f","χ":"x","ψ":"y","ω":"o",
    "А":"A","В":"B","С":"C","Е":"E","Н":"H","К":"K","М":"M","О":"O",
    "Р":"P","Т":"T","У":"Y","Х":"X",
    "а":"a","в":"b","е":"e","к":"k","м":"m","н":"n","о":"o",
    "р":"p","с":"c","т":"t","у":"y","х":"x",
}

# ─── Runtime state ────────────────────────────────────────────────────────────

FAMILY_METRICS: dict[str, dict[str, dict[str, int]]] = {}

# ─── Inter download ───────────────────────────────────────────────────────────

def _inter_zip_is_valid() -> bool:
    """Return True only if the cached zip exists and is a valid ZIP file."""
    if not os.path.exists(INTER_ZIP_CACHE):
        return False
    try:
        with zipfile.ZipFile(INTER_ZIP_CACHE) as zf:
            bad = zf.testzip()
            if bad:
                log.warning("Cached Inter zip is corrupt (first bad file: %s)", bad)
                return False
        return True
    except zipfile.BadZipFile:
        log.warning("Cached Inter zip is not a valid ZIP file")
        return False


def download_inter_zip() -> str:
    """Download Inter v4.1 release zip to BASECACHE if not already present and valid."""
    if _inter_zip_is_valid():
        log.info("✓ Found cached Inter zip")
        return INTER_ZIP_CACHE

    if os.path.exists(INTER_ZIP_CACHE):
        log.warning("Removing corrupt/partial Inter zip cache")
        os.remove(INTER_ZIP_CACHE)

    log.info("Downloading Inter v4.1…")
    tmp = INTER_ZIP_CACHE + ".part"
    try:
        r = requests.get(INTER_RELEASE_URL, stream=True)
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                fh.write(chunk)
        # Validate before promoting to final path
        if not zipfile.is_zipfile(tmp):
            raise RuntimeError("Downloaded file is not a valid ZIP")
        os.replace(tmp, INTER_ZIP_CACHE)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    log.info("✓ Downloaded → %s", INTER_ZIP_CACHE)
    return INTER_ZIP_CACHE


def extract_base(style_filename: str) -> str:
    """Extract one static Inter TTF from the release zip."""
    dest = os.path.join(BASECACHE, style_filename)
    if os.path.exists(dest):
        log.info("✓ Found %s", style_filename)
        return dest
    with zipfile.ZipFile(download_inter_zip()) as zf:
        match = next(
            (e for e in zf.namelist()
             if e.endswith(f"/{style_filename}") or e == style_filename),
            None,
        )
        if match is None:
            available = [e for e in zf.namelist() if e.endswith(".ttf")]
            raise FileNotFoundError(
                f"{style_filename} not found in Inter zip. "
                f"Available TTFs: {available}"
            )
        with zf.open(match) as src, open(dest, "wb") as out:
            out.write(src.read())
    log.info("✓ Extracted %s", style_filename)
    return dest

# ─── Low-level helpers ────────────────────────────────────────────────────────

def get_base_letter(ch: str) -> str:
    """Strip diacritics and return the base Latin letter."""
    for c in unicodedata.normalize("NFD", ch):
        if c.isalpha():
            return c
    return ch


def set_coords(
    glyph: Any,
    coords: list[tuple[int, int]],
    end_pts: list[int],
    flags: list[int],
) -> None:
    """Write coordinate data back to a glyph in place."""
    if len(coords) != len(flags):
        flags = list(flags) + [flags[-1]] * abs(len(coords) - len(flags))
    glyph.coordinates      = GlyphCoordinates(coords)
    glyph.endPtsOfContours = end_pts
    glyph.flags            = flags


def ensure_program(glyph: Any) -> None:
    """Attach an empty hinting program if the attribute is absent."""
    from fontTools.ttLib.tables.ttProgram import Program
    if not hasattr(glyph, "program") or glyph.program is None:
        glyph.program = Program()

# ─── GSUB disambiguation baking ──────────────────────────────────────────────

def verify_inter_gsub(tt: TTFont) -> None:
    """Confirm the base font is Inter and has expected GSUB features."""
    gsub = tt.get("GSUB")
    if not gsub or not gsub.table.FeatureList:
        raise RuntimeError(
            "No GSUB table — this does not appear to be Inter."
        )
    found = {fr.FeatureTag for fr in gsub.table.FeatureList.FeatureRecord}
    for tag in ("ss02", "cv05"):
        if tag in found:
            log.info("✓ GSUB '%s' present", tag)
        else:
            log.warning("GSUB '%s' absent — baking will skip it", tag)
    if "ss02" not in found:
        raise RuntimeError(
            f"ss02 missing. Inter v4.0+ required. Found: {sorted(found)}"
        )


def bake_disambiguation_defaults(
    tt: TTFont,
    feature_tags: frozenset[str] = frozenset({"ss02", "cv05"}),
) -> None:
    """Copy Inter's disambiguation alternates into the default glyph slots.

    Inter's ss02 set has professionally drawn alternates for I (with serifs),
    l (with foot curve), slashed zero, and other confusable glyphs. cv05
    provides a distinct lowercase l. Baking them into the defaults means
    every reader gets the benefit without needing CSS font-feature-settings.
    """
    gsub = tt.get("GSUB")
    if not gsub:
        log.warning("No GSUB — skipping disambiguation baking")
        return
    table = gsub.table
    if not table.FeatureList or not table.LookupList:
        return

    target_lookups: set[int] = set()
    for fr in table.FeatureList.FeatureRecord:
        if fr.FeatureTag in feature_tags:
            target_lookups.update(fr.Feature.LookupListIndex)

    substitutions: dict[str, str] = {}
    for idx in sorted(target_lookups):
        for sub in table.LookupList.Lookup[idx].SubTable:
            if hasattr(sub, "mapping"):
                substitutions.update(sub.mapping)

    if not substitutions:
        log.warning("No SingleSubst mappings found in target GSUB lookups")
        return

    glyf  = tt["glyf"]
    hmtx  = tt["hmtx"].metrics
    baked = skipped = 0

    for default_name, alt_name in substitutions.items():
        if default_name not in glyf or alt_name not in glyf:
            skipped += 1
            continue
        alt     = glyf[alt_name]
        default = glyf[default_name]
        default.numberOfContours = alt.numberOfContours
        if alt.numberOfContours >= 0:
            coords, end_pts, flags = alt.getCoordinates(glyf)
            default.coordinates      = GlyphCoordinates(coords)
            default.endPtsOfContours = list(end_pts)
            default.flags            = list(flags)
            if hasattr(default, "components"):
                default.components = []
            default.program = (
                alt.program
                if hasattr(alt, "program") and alt.program is not None
                else __import__(
                    "fontTools.ttLib.tables.ttProgram", fromlist=["Program"]
                ).Program()
            )
        elif alt.isComposite():
            default.components = list(alt.components)
            for attr in ("coordinates", "endPtsOfContours", "flags"):
                if hasattr(default, attr):
                    delattr(default, attr)
            if hasattr(alt, "program") and alt.program is not None:
                default.program = alt.program
            elif hasattr(default, "program"):
                del default.program

        if alt_name in hmtx and default_name in hmtx:
            alt_adv, _      = hmtx[alt_name]
            _, default_lsb  = hmtx[default_name]
            hmtx[default_name] = (alt_adv, default_lsb)

        log.info("  ✓ Baked: %s ← %s", default_name, alt_name)
        baked += 1

    log.info("✓ GSUB baking: %d promoted, %d skipped", baked, skipped)

# ─── Optical entry anchoring ──────────────────────────────────────────────────

def apply_optical_anchor(
    tt: TTFont, entry_band: float, global_strength: float
) -> None:
    """Shift entry-side glyph points leftward to create fixation anchors.

    Covers Latin, Latin-Extended, Greek, and Cyrillic. Each glyph is
    given a tapered leftward shift across the entry_band fraction of its
    width, scaled by the per-character strength from FONT_PARAMS.
    """
    glyf     = tt["glyf"]
    cmap     = tt.getBestCmap() or {}
    affected = 0

    for code, gname in cmap.items():
        ch = chr(code)
        if not (
            ("\u0000" <= ch <= "\u024F")
            or ("\u1E00" <= ch <= "\u1EFF")
            or ("\u0370" <= ch <= "\u03FF")
            or ("\u0400" <= ch <= "\u04FF")
        ):
            continue
        base     = ANCHOR_BASE_MAP.get(ch, get_base_letter(ch))
        strength = (
            FONT_PARAMS["anchor_lc"].get(base)
            or FONT_PARAMS["anchor_uc"].get(base)
        )
        if not strength:
            continue
        g = glyf[gname]
        if not hasattr(g, "getCoordinates"):
            continue
        coords, end_pts, flags = g.getCoordinates(glyf)
        if not coords:
            continue

        s     = strength * global_strength
        xs    = [x for x, _ in coords]
        x_min = min(xs)
        width = max(1, max(xs) - x_min)
        new_coords = [
            (
                int(x - s * (1.0 - (x - x_min) / width / entry_band) * width)
                if (x - x_min) / width <= entry_band
                else x,
                y,
            )
            for x, y in coords
        ]
        set_coords(g, new_coords, list(end_pts), list(flags))
        affected += 1

    log.info("✓ Anchoring: %d glyphs (strength=%.2f)", affected, global_strength)

# ─── X-height scaling ─────────────────────────────────────────────────────────

def raise_xheight(tt: TTFont, factor: float) -> None:
    """Scale only the x-height zone; translate ascenders by the same delta.

    Naive y*factor scaling would also enlarge ascenders, compressing the
    ascender/x-height ratio. This function scales y in (0, xheight_y]
    and shifts y > xheight_y by the absolute delta, keeping ascender
    height constant while genuinely raising the x-height.
    """
    if abs(factor - 1.0) < 1e-3:
        return
    os2       = tt["OS/2"]
    xheight_y = int(getattr(os2, "sxHeight", 0))
    if xheight_y <= 0:
        raise ValueError("OS/2.sxHeight must be positive before raise_xheight")
    new_xh  = int(round(xheight_y * factor))
    delta_y = new_xh - xheight_y
    glyf    = tt["glyf"]

    for code, gname in (tt.getBestCmap() or {}).items():
        if not chr(code).islower():
            continue
        g = glyf[gname]
        if not hasattr(g, "getCoordinates"):
            continue
        coords, end_pts, flags = g.getCoordinates(glyf)
        if not coords:
            continue
        updated = [
            (x, int(round(y * factor)) if 0 < y <= xheight_y
             else y + delta_y if y > xheight_y
             else y)
            for x, y in coords
        ]
        set_coords(g, updated, list(end_pts), list(flags))

    os2.sxHeight = new_xh
    log.info("✓ x-height ×%.2f (ascenders translated, not scaled)", factor)


def validate_proportions(tt: TTFont, family: str, style: str) -> None:
    """Halt the build if x-height scaling has broken ascender/descender ratios."""
    os2  = tt["OS/2"]
    xh   = int(os2.sxHeight)
    asc  = int(os2.sTypoAscender)
    desc = abs(int(os2.sTypoDescender))
    p    = FONT_PARAMS["proportions"]
    if asc < xh * p["ascender_xheight_ratio"]:
        raise ValueError(
            f"Proportion fail [{family} {style}]: asc={asc} xh={xh}"
        )
    if desc < xh * p["descender_xheight_ratio"]:
        raise ValueError(
            f"Proportion fail [{family} {style}]: desc={desc} xh={xh}"
        )
    log.info(
        "✓ Proportions OK [%s %s]: asc=%d xh=%d desc=%d",
        family, style, asc, xh, desc,
    )

# ─── Stem-shift disambiguation ────────────────────────────────────────────────

def apply_stem_shift_disambiguation(tt: TTFont) -> None:
    """Shift the extreme terminus point of specific stems outward.

    For each codepoint in STEM_SHIFT_MAP, finds the extreme point of the
    relevant stem (top-left for b-type, bottom-left/right for p/q-type)
    and moves it laterally. No new points are added. The adjacent Bezier
    control points remain in place, so the curve naturally bends to create
    a diagonal shoulder — exactly as a type designer would widen a stem
    terminal in a font editor.

    b and p (top_left, bottom_left) use a reduced shift because the bowl
    junction already adds optical mass to the stem side. q (bottom_right)
    uses the full shift since its descender tip is more visually isolated.

    This is the simplest possible approach: move one point, let the math
    do the rest. Robust across weights and hinting passes.
    """
    cfg = FONT_PARAMS["stem_shift"]
    if not cfg["enabled"]:
        return

    from fontTools.ttLib.tables.ttProgram import Program

    cmap           = tt.getBestCmap() or {}
    glyf           = tt["glyf"]
    upm            = tt["head"].unitsPerEm
    shift_full     = int(upm * cfg["shoulder_width"])
    shift_reduced  = int(upm * cfg["shoulder_width_reduced"])
    tol            = int(upm * cfg["y_tolerance"])
    applied        = 0

    for codepoint, position in STEM_SHIFT_MAP.items():
        glyph_name = cmap.get(codepoint)
        if not glyph_name:
            log.warning("StemShift: U+%04X not in cmap — skipped", codepoint)
            continue

        glyph = glyf.get(glyph_name)
        if glyph is None or not hasattr(glyph, "getCoordinates"):
            continue
        if glyph.numberOfContours <= 0:
            continue

        coords, end_pts, flags = glyph.getCoordinates(glyf)
        coords = list(coords)
        ys     = [y for _, y in coords]

        # Find the cluster of points near the extreme y
        extreme = max(ys) if position in (StemPosition.top_left, StemPosition.top_right) else min(ys)
        cluster = [
            (i, x, y) for i, (x, y) in enumerate(coords)
            if abs(y - extreme) <= tol
        ]
        if not cluster:
            log.warning("StemShift: no cluster found for U+%04X", codepoint)
            continue

        # b/p (bowl-side stems) get a reduced shift to compensate for the
        # optical mass the bowl junction adds. q gets the full shift.
        s = shift_reduced if position in (StemPosition.top_left, StemPosition.bottom_left) else shift_full

        if position in (StemPosition.top_left, StemPosition.bottom_left):
            ti, sx, sy = min(cluster, key=lambda t: t[1])
            coords[ti] = (sx - s, sy)
        else:
            ti, sx, sy = max(cluster, key=lambda t: t[1])
            coords[ti] = (sx + s, sy)

        glyph.coordinates = GlyphCoordinates(coords)
        glyph.program     = Program()

        log.info(
            "  ✓ StemShift [%s] U+%04X (%s) pt%d (%d,%d) → (%d,%d)  shift=%d",
            position.value, codepoint, chr(codepoint),
            ti, sx, sy, coords[ti][0], coords[ti][1], s,
        )
        applied += 1

    log.info(
        "✓ Stem-shift disambiguation: %d/%d glyphs  "
        "(full=%d units, reduced=%d units)",
        applied, len(STEM_SHIFT_MAP), shift_full, shift_reduced,
    )

# ─── Spacing ──────────────────────────────────────────────────────────────────

def apply_comfort_spacing(
    tt: TTFont, letter_factor: float, word_factor: float
) -> None:
    """Scale advance widths; space glyph uses a separate word factor."""
    hmtx = tt["hmtx"].metrics
    for gname, (adv, lsb) in list(hmtx.items()):
        if gname == "space":
            continue
        hmtx[gname] = (max(1, int(round(adv * letter_factor))), lsb)
    if "space" in hmtx:
        adv, lsb = hmtx["space"]
        hmtx["space"] = (max(1, int(round(adv * word_factor))), lsb)
    log.info("✓ Spacing: letters×%.2f words×%.2f", letter_factor, word_factor)


def apply_micro_spacing(tt: TTFont, level: float) -> None:
    """Apply per-character advance-width fine-tuning from FONT_PARAMS."""
    if level <= 0:
        return
    upm   = tt["head"].unitsPerEm
    cmap  = tt.getBestCmap() or {}
    hmtx  = tt["hmtx"].metrics
    table = FONT_PARAMS["micro_spacing_em"]
    n     = 0
    for code, gname in cmap.items():
        ch  = chr(code)
        key = table.get(ch) or table.get(get_base_letter(ch))
        if not key or gname not in hmtx:
            continue
        adv, lsb = hmtx[gname]
        hmtx[gname] = (max(1, adv + int(round(key * level * upm))), lsb)
        n += 1
    log.info("✓ Micro-spacing: %d glyphs", n)

# ─── Naming ───────────────────────────────────────────────────────────────────

def set_naming(
    tt: TTFont, family: str, style_key: str, style_label: str, weight: int
) -> None:
    """Write Google Fonts-compatible name records and OS/2 style flags."""
    nm           = tt["name"]
    family_label = FAMILY_DISPLAY.get(family, family)
    ps_name      = f"{family.replace(' ', '')}-{style_key}"

    nm.names = [n for n in nm.names if n.nameID not in (1, 2, 4, 5, 6, 16)]
    nm.removeNames(nameID=16)
    for nid, val in [
        (1, family_label),
        (2, style_label),
        (4, f"{family_label} {style_label}"),
        (5, f"Version {VERSION_DECIMAL}"),
        (6, ps_name),
    ]:
        nm.setName(val, nid, 3, 1, 0x409)

    if "OS/2" in tt:
        os2 = tt["OS/2"]
        os2.usWeightClass = weight
        sel = (
            (1 << 6 if "Regular" in style_label else 0)
            | (1 << 5 if "Bold"    in style_label else 0)
            | (1 << 0 if "Italic"  in style_label else 0)
        )
        os2.fsSelection &= ~((1 << 0) | (1 << 5) | (1 << 6))
        os2.fsSelection |= sel | (1 << 7)

    if "head" in tt:
        tt["head"].fontRevision = float(fractions.Fraction(VERSION_DECIMAL))

    log.info("✓ Naming: %s", ps_name)

# ─── Metric utilities ─────────────────────────────────────────────────────────

def ensure_win_metrics(tt: TTFont) -> None:
    """Clamp Windows ascent/descent to safe minimums."""
    head = tt["head"]
    os2  = tt["OS/2"]
    os2.usWinAscent  = max(os2.usWinAscent,  head.yMax,
                           FONT_PARAMS["win_ascent_min"])
    os2.usWinDescent = max(os2.usWinDescent, abs(head.yMin),
                           FONT_PARAMS["win_descent_min"])


def recompute_xavg(tt: TTFont) -> None:
    """Recalculate OS/2.xAvgCharWidth from current advance widths."""
    vals = [adv for adv, _ in tt["hmtx"].metrics.values() if adv > 0]
    if vals:
        tt["OS/2"].xAvgCharWidth = int(round(sum(vals) / len(vals)))


def post_hint_fixup(font_path: str) -> None:
    """Apply final metric fixups after hinting."""
    tt = TTFont(font_path)
    ensure_win_metrics(tt)
    recompute_xavg(tt)
    tt["head"].flags |= 1 << 3  # force ppem to integer
    tt.save(font_path)

# ─── Glyph utilities ──────────────────────────────────────────────────────────

def remove_soft_hyphen(tt: TTFont) -> None:
    """Delete the soft-hyphen (U+00AD) cmap entry."""
    cmap = tt.getBestCmap()
    if cmap and 0x00AD in cmap:
        log.info("✓ Removing soft-hyphen (glyph: %s)", cmap[0x00AD])
        for table in tt["cmap"].tables:
            if table.isUnicode() and 0x00AD in table.cmap:
                del table.cmap[0x00AD]


def ensure_minus_glyph(tt: TTFont) -> None:
    """Clone a hyphen to U+2212 (MINUS SIGN) when absent."""
    cmap = tt.getBestCmap() or {}
    if 0x2212 in cmap:
        return
    order    = list(tt.getGlyphOrder())
    src_name = next(
        (c for c in ("minus", "uni2212", "hyphen", "uni2010") if c in order),
        None,
    )
    if not src_name:
        return
    glyf = tt["glyf"]
    src  = glyf[src_name]
    new  = src.__class__()
    new.numberOfContours = src.numberOfContours
    if src.numberOfContours >= 0:
        coords, end_pts, flags = src.getCoordinates(glyf)
        new.coordinates      = GlyphCoordinates(coords)
        new.endPtsOfContours = list(end_pts)
        new.flags            = list(flags)
        ensure_program(new)
        if hasattr(src, "program") and src.program is not None:
            new.program = src.program
    else:
        new.components = list(src.components)
    glyf["uni2212"] = new
    order.append("uni2212")
    tt.setGlyphOrder(order)
    if src_name in tt["hmtx"].metrics:
        tt["hmtx"].metrics["uni2212"] = tt["hmtx"].metrics[src_name]
    for table in tt["cmap"].tables:
        if table.isUnicode():
            table.cmap[0x2212] = "uni2212"


def sync_space_nbspace(tt: TTFont) -> None:
    """Keep non-breaking space width in sync with regular space."""
    hmtx = tt["hmtx"].metrics
    if "space" not in hmtx:
        return
    adv, lsb = hmtx["space"]
    for name in ("nbspace", "nonbreakingspace", "uni00A0"):
        if name in hmtx:
            hmtx[name] = (adv, lsb)


def sanitize_gdef_marks(tt: TTFont) -> None:
    """Downgrade spacing marks incorrectly classed as non-spacing."""
    if "GDEF" not in tt:
        return
    gc = getattr(tt["GDEF"].table, "GlyphClassDef", None)
    if not gc or not gc.classDefs:
        return
    hmtx = tt["hmtx"].metrics
    for gname, cls_id in list(gc.classDefs.items()):
        if cls_id == 3 and gname in hmtx and hmtx[gname][0] != 0:
            gc.classDefs[gname] = 1


def sanitize_stat_table(tt: TTFont) -> None:
    """Remove duplicate STAT axis values."""
    stat = tt.get("STAT")
    if not stat:
        return
    values = stat.table.AxisValueArray.AxisValue
    seen, filtered = set(), []
    for v in values:
        ai = getattr(v, "AxisIndex", None)
        if ai is None or ai not in seen:
            filtered.append(v)
            if ai is not None:
                seen.add(ai)
    if len(filtered) < len(values):
        stat.table.AxisValueArray.AxisValue = filtered
        stat.table.AxisValueCount = len(filtered)
        log.info("✓ STAT: removed %d duplicates", len(values) - len(filtered))


def clone_glyph(
    tt: TTFont, src_name: str, dst_name: str, target_code: int
) -> None:
    """Clone a glyph outline to a new Unicode codepoint."""
    glyf  = tt["glyf"]
    order = list(tt.getGlyphOrder())
    if dst_name in glyf or src_name not in glyf:
        return
    src = glyf[src_name]
    new = src.__class__()
    new.numberOfContours = src.numberOfContours
    if src.numberOfContours >= 0:
        coords, end_pts, flags = src.getCoordinates(glyf)
        new.coordinates      = GlyphCoordinates(coords)
        new.endPtsOfContours = list(end_pts)
        new.flags            = list(flags)
        ensure_program(new)
        if hasattr(src, "program") and src.program is not None:
            new.program = src.program
    else:
        new.components = list(src.components)
        if hasattr(src, "program"):
            new.program = src.program
    glyf[dst_name] = new
    order.append(dst_name)
    tt.setGlyphOrder(order)
    if src_name in tt["hmtx"].metrics:
        tt["hmtx"].metrics[dst_name] = tt["hmtx"].metrics[src_name]
    for table in tt["cmap"].tables:
        if table.isUnicode():
            table.cmap[target_code] = dst_name


def ensure_case_pairs(tt: TTFont) -> None:
    """Clone missing upper/lowercase pairs for cmap completeness."""
    cmap = tt.getBestCmap() or {}
    for cp, gname in list(cmap.items()):
        ch  = chr(cp)
        upr = unicodedata.normalize("NFC", ch).upper()
        lwr = unicodedata.normalize("NFC", ch).lower()
        if len(upr) != 1 or len(lwr) != 1:
            continue
        for target in (ord(upr), ord(lwr)):
            if target != cp and target not in cmap:
                clone_glyph(tt, gname, f"uni{target:04X}", target)

# ─── Composite flattening ─────────────────────────────────────────────────────

IDENTITY_TRANSFORM = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _compose_transforms(
    parent: tuple[float, ...], child: tuple[float, ...]
) -> tuple[float, ...]:
    a1, b1, c1, d1, e1, f1 = parent
    a2, b2, c2, d2, e2, f2 = child
    return (
        a1*a2 + b1*c2, a1*b2 + b1*d2,
        c1*a2 + d1*c2, c1*b2 + d1*d2,
        e1 + a1*e2 + b1*f2,
        f1 + c1*e2 + d1*f2,
    )


def _draw_as_contours(
    tt: TTFont, glyph_name: str, pen: TTGlyphPen,
    transform: tuple[float, ...] = IDENTITY_TRANSFORM,
) -> None:
    glyph = tt["glyf"][glyph_name]
    if glyph.isComposite():
        for comp in glyph.components:
            cname, ctrans = comp.getComponentInfo()
            _draw_as_contours(
                tt, cname, pen, _compose_transforms(transform, ctrans)
            )
        return
    used = pen if transform == IDENTITY_TRANSFORM else TransformPen(pen, transform)
    glyph.draw(used, tt["glyf"])


def flatten_composites(tt: TTFont) -> None:
    """Replace all composite glyphs with simple contours before saving."""
    glyf = tt["glyf"]
    for gname in tt.getGlyphOrder():
        g = glyf[gname]
        if not g.isComposite():
            continue
        pen = TTGlyphPen(glyf)
        _draw_as_contours(tt, gname, pen)
        new = pen.glyph()
        if hasattr(g, "program") and g.program is not None:
            new.program = g.program
        else:
            ensure_program(new)
        glyf[gname] = new

# ─── Vertical metrics snapshot ────────────────────────────────────────────────

def capture_metrics_snapshot(tt: TTFont) -> dict[str, dict[str, int]]:
    snap: dict[str, dict[str, int]] = {}
    if "hhea" in tt:
        h = tt["hhea"]
        snap["hhea"] = {
            "ascent": h.ascent, "descent": h.descent, "lineGap": h.lineGap
        }
    if "OS/2" in tt:
        o = tt["OS/2"]
        snap["OS/2"] = {
            "sTypoAscender":  o.sTypoAscender,
            "sTypoDescender": o.sTypoDescender,
            "sTypoLineGap":   o.sTypoLineGap,
            "usWinAscent":    o.usWinAscent,
            "usWinDescent":   o.usWinDescent,
        }
    return snap


def apply_metrics_snapshot(tt: TTFont, family: str) -> None:
    """Re-apply the Regular style's metrics to italic/bold variants."""
    snap = FAMILY_METRICS.get(family)
    if not snap:
        return
    if "hhea" in tt and "hhea" in snap:
        h = tt["hhea"]; d = snap["hhea"]
        h.ascent = d["ascent"]
        h.descent = d["descent"]
        h.lineGap = d["lineGap"]
    if "OS/2" in tt and "OS/2" in snap:
        o = tt["OS/2"]; d = snap["OS/2"]
        o.sTypoAscender  = d["sTypoAscender"]
        o.sTypoDescender = d["sTypoDescender"]
        o.sTypoLineGap   = d["sTypoLineGap"]
        o.usWinAscent    = d["usWinAscent"]
        o.usWinDescent   = d["usWinDescent"]

# ─── Hinting ──────────────────────────────────────────────────────────────────

def auto_hint(in_path: str, out_path: str, enabled: bool = True) -> bool:
    """Run ttfautohint when available and not disabled."""
    if not enabled:
        log.info("→ Hinting skipped (--no-hint)")
        return False
    bin_path = shutil.which("ttfautohint")
    if not bin_path:
        log.warning("ttfautohint not found; skipping")
        return False
    result = subprocess.run(
        [bin_path, "--windows-compatibility", "--symbol", "--no-info",
         in_path, out_path],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        log.warning("ttfautohint failed: %s", result.stderr.strip())
        return False
    log.info("✓ Hinted → %s", os.path.basename(out_path))
    return True

# ─── WOFF2 compression ────────────────────────────────────────────────────────

def compress_to_woff2(ttf_path: str) -> None:
    """Compress a TTF to WOFF2 when woff2_compress is available."""
    woff2_bin = os.environ.get("WOFF2_BIN") or shutil.which("woff2_compress")
    if not woff2_bin:
        log.warning("woff2_compress not found; skipping")
        return

    ttf_dir   = os.path.dirname(ttf_path)
    ttf_base  = os.path.basename(ttf_path)
    out_woff  = os.path.join(OUT_WEB, ttf_base.replace(".ttf", ".woff2"))
    generated = os.path.join(ttf_dir, ttf_base.replace(".ttf", ".woff2"))

    try:
        subprocess.run(
            [woff2_bin, ttf_base], cwd=ttf_dir, check=True, capture_output=True
        )
        shutil.move(generated, out_woff)
        log.info("✓ WOFF2: %s", os.path.basename(out_woff))
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else str(exc.stderr)
        log.warning("woff2_compress failed: %s", stderr)
    except FileNotFoundError:
        log.warning("Generated .woff2 not found for %s", ttf_base)

# ─── Core build ───────────────────────────────────────────────────────────────

def build_one(
    src_path: str, out_path: str,
    family: str, style_key: str, style_label: str, weight: int,
    cfg: FamilyConfig, hinting_enabled: bool = True,
) -> dict[str, Any]:
    """Build one font style. Returns metrics for the build report."""
    tt = TTFont(src_path)

    # 1. Bake Inter's built-in alternates (slashed zero, l-foot, I-serifs…)
    bake_disambiguation_defaults(tt)

    # 2. Optical entry anchoring (must run before stem-shift so the
    #    shifted point is not treated as the new leftmost anchor target)
    apply_optical_anchor(tt, FONT_PARAMS["entry_band"], cfg.anchor_strength)

    # 3. Stem-shift disambiguation — move one point per glyph, no insertion
    apply_stem_shift_disambiguation(tt)

    # 4. X-height scaling (zone-only; ascenders translated, not scaled)
    raise_xheight(tt, cfg.xheight_factor)

    # 5. Spacing
    apply_comfort_spacing(tt, cfg.letter_spacing, cfg.word_spacing)
    apply_micro_spacing(tt, cfg.micro_level)

    # 6. Metadata and cmap completeness
    set_naming(tt, family, style_key, style_label, weight)
    ensure_minus_glyph(tt)
    remove_soft_hyphen(tt)
    sync_space_nbspace(tt)
    ensure_case_pairs(tt)

    # 7. Structural cleanup
    flatten_composites(tt)
    sanitize_gdef_marks(tt)
    sanitize_stat_table(tt)

    # 8. Lock in family-wide vertical metrics (Regular style sets the snapshot)
    if FAMILY_METRICS.get(family):
        apply_metrics_snapshot(tt, family)

    # 9. Guard against proportion regressions
    validate_proportions(tt, family, style_label)

    # 10. Save → hint → post-fixup
    tmp = out_path.replace(".ttf", "-tmp.ttf")
    tt.save(tmp)
    if not auto_hint(tmp, out_path, enabled=hinting_enabled):
        shutil.move(tmp, out_path)
    else:
        os.remove(tmp)
    post_hint_fixup(out_path)
    log.info("→ %s", os.path.basename(out_path))

    # 11. Collect report metrics
    saved = TTFont(out_path)
    os2   = saved["OS/2"]
    return {
        "glyph_count": len(saved.getGlyphOrder()),
        "os2": {
            "xHeight":   int(os2.sxHeight),
            "ascender":  int(os2.sTypoAscender),
            "descender": int(os2.sTypoDescender),
        },
        "params": {
            "anchor_strength": cfg.anchor_strength,
            "xheight_factor":  cfg.xheight_factor,
            "letter_spacing":  cfg.letter_spacing,
            "word_spacing":    cfg.word_spacing,
        },
    }

# ─── CLI ──────────────────────────────────────────────────────────────────────

def resolve_family_filter(name: str | None) -> dict[str, FamilyConfig]:
    if not name:
        return FAMILIES
    wanted = name.casefold()
    for k, v in FAMILIES.items():
        if k.casefold() == wanted:
            return {k: v}
    raise ValueError(
        f"Unknown family '{name}'. Options: {list(FAMILIES)}"
    )


def get_git_commit() -> str:
    r = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    return r.stdout.strip() or "unknown"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build EasyType fonts.")
    p.add_argument("--dry-run",  action="store_true",
                   help="Validate without writing files.")
    p.add_argument("--family",
                   help='Build one family, e.g. --family "EasyType Steady".')
    p.add_argument("--no-hint", action="store_true",
                   help="Skip ttfautohint.")
    p.add_argument("--version", action="version", version=VERSION_STR)
    return p.parse_args()

# ─── Main ─────────────────────────────────────────────────────────────────────

def _build_family(
    family: str, cfg: FamilyConfig, bases: dict[str, str],
    hinting_enabled: bool,
) -> tuple[str, dict[str, Any]]:
    """Build all 4 styles for one family and return (family_name, family_report).

    Regular is built first (to capture the metrics snapshot), then the
    remaining 3 styles are built in parallel.
    """
    log.info("=== Building %s ===", family)
    family_report: dict[str, Any] = {}

    # Regular must come first — its metrics snapshot is applied to other styles.
    reg_style, (reg_weight, reg_label) = "Regular", STYLE_WEIGHTS["Regular"]
    out_ttf_reg = os.path.join(OUT_TTF, f"{family.replace(' ', '')}-{reg_style}.ttf")
    family_report[reg_style] = build_one(
        bases[reg_style], out_ttf_reg, family, reg_style, reg_label, reg_weight,
        cfg, hinting_enabled=hinting_enabled,
    )
    FAMILY_METRICS[family] = capture_metrics_snapshot(TTFont(out_ttf_reg))
    compress_to_woff2(out_ttf_reg)

    # Remaining styles share no state — build in parallel.
    other_styles = [(s, w, l) for s, (w, l) in STYLE_WEIGHTS.items() if s != "Regular"]

    def _build_style(style: str, weight: int, style_label: str) -> tuple[str, dict[str, Any]]:
        out_ttf = os.path.join(OUT_TTF, f"{family.replace(' ', '')}-{style}.ttf")
        report  = build_one(
            bases[style], out_ttf, family, style, style_label, weight,
            cfg, hinting_enabled=hinting_enabled,
        )
        compress_to_woff2(out_ttf)
        return style, report

    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures = {pool.submit(_build_style, s, w, l): s for s, w, l in other_styles}
        for fut in concurrent.futures.as_completed(futures):
            style, style_report = fut.result()
            family_report[style] = style_report

    return family, family_report


def main() -> int:
    args     = parse_args()
    families = resolve_family_filter(args.family)
    bases    = {sty: extract_base(fname) for sty, fname in BASES.items()}

    verify_inter_gsub(TTFont(bases["Regular"]))

    report: dict[str, Any] = {
        "version":    VERSION_DISPLAY,
        "built_at":   dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "families":   {},
    }

    if args.dry_run:
        for family, cfg in families.items():
            log.info("=== Dry-run %s ===", family)
            for style, (_, style_label) in STYLE_WEIGHTS.items():
                tt = TTFont(bases[style])
                bake_disambiguation_defaults(tt)
                apply_optical_anchor(tt, FONT_PARAMS["entry_band"], cfg.anchor_strength)
                apply_stem_shift_disambiguation(tt)
                raise_xheight(tt, cfg.xheight_factor)
                validate_proportions(tt, family, style_label)
                log.info("  dry-run OK: %s %s", family, style_label)
        log.info("✓ Dry run complete")
        return 0

    # Build all families in parallel (each family builds Regular first, then
    # its remaining 3 styles in parallel, so the total work is fully pipelined).
    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures = {
            pool.submit(_build_family, family, cfg, bases, not args.no_hint): family
            for family, cfg in families.items()
        }
        for fut in concurrent.futures.as_completed(futures):
            family, family_report = fut.result()
            report["families"][family] = family_report

    os.makedirs(os.path.dirname(BUILD_REPORT_PATH), exist_ok=True)
    with open(BUILD_REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    log.info("✓ Build report → %s", BUILD_REPORT_PATH)
    log.info(
        "✅ Done — version %s; families: %s",
        VERSION_DISPLAY, ", ".join(report["families"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

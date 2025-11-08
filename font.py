#!/usr/bin/env python3
"""
EasyType Font Builder — moderated optical anchoring, Latin coverage, micro-spacing
Outputs:
  fonts/ttf/*.ttf
  fonts/web/*.woff2

Requires:
  pip install fonttools requests
Optional:
  brew install woff2      (macOS) — override path via env: WOFF2_BIN=/custom/path/woff2_compress
"""

import os, sys, subprocess, unicodedata, requests
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

# ----------------------- Paths -----------------------
URL_BASE = "https://github.com/notofonts/noto-fonts/raw/main/hinted/ttf/NotoSans/"
BASES = {
    "Regular":    "NotoSans-Regular.ttf",
    "Italic":     "NotoSans-Italic.ttf",
    "Bold":       "NotoSans-Bold.ttf",
    "BoldItalic": "NotoSans-BoldItalic.ttf",
}
BASECACHE = "./base_fonts"
OUT_TTF   = "./fonts/ttf"
OUT_WEB   = "./fonts/web"
os.makedirs(BASECACHE, exist_ok=True)
os.makedirs(OUT_TTF,   exist_ok=True)
os.makedirs(OUT_WEB,   exist_ok=True)

# -------------------- Family presets -----------------
# Moderated, evidence-aligned defaults
FAMILIES = {
    # family_name : (weights, global_anchor, xheight, letter_spacing, word_spacing, micro_level)
    "EasyType Sans":     ({"Regular":400,"Italic":400,"Bold":700,"BoldItalic":700}, 0.25, 1.02, 1.06, 1.12, 0.8),
    "EasyType Focus":    ({"Regular":400,"Italic":400,"Bold":700,"BoldItalic":700}, 0.40, 1.06, 1.14, 1.24, 1.0),
    "EasyType Dyslexic": ({"Regular":400,"Italic":400,"Bold":700,"BoldItalic":700}, 0.55, 1.10, 1.22, 1.32, 1.0),
}

VERSION_STR = "EasyType v1.0.0"

# -------------------- Anchoring ----------------------
# Entry band kept tight to avoid distortion
ENTRY_BAND = 0.18  # fraction of glyph width affected

# Per-letter base strengths (moderated vs your earlier table)
# Lowercase
ANCHOR_LC = {
    "a": 0.28, "b": 0.16, "c": 0.34, "d": 0.22, "e": 0.32, "f": 0.12, "g": 0.26, "h": 0.16,
    "i": 0.10, "j": 0.11, "k": 0.13, "l": 0.10, "m": 0.20, "n": 0.18, "o": 0.32, "p": 0.22,
    "q": 0.22, "r": 0.18, "s": 0.24, "t": 0.16, "u": 0.22, "v": 0.14, "w": 0.16, "x": 0.12,
    "y": 0.16, "z": 0.12
}
# Uppercase (milder)
ANCHOR_UC = {
    "A": 0.08, "B": 0.20, "C": 0.22, "D": 0.20, "E": 0.22, "F": 0.20, "G": 0.22, "H": 0.18,
    "I": 0.00, "J": 0.20, "K": 0.20, "L": 0.22, "M": 0.20, "N": 0.20, "O": 0.22, "P": 0.20,
    "Q": 0.22, "R": 0.20, "S": 0.22, "T": 0.18, "U": 0.20, "V": 0.16, "W": 0.18, "X": 0.14,
    "Y": 0.16, "Z": 0.14
}

# -------------------- Micro spacing ------------------
# EM fractions (±) applied as advance-width deltas; moderated
MICRO_SPACING_EM = {
    # widen slightly (rhythm)
    "m": +0.010, "w": +0.009, "M": +0.012, "W": +0.012,
    "g": +0.008, "G": +0.010, "Q": +0.010, "8": +0.010, "0": +0.006,
    "n": +0.006, "h": +0.006, "u": +0.006, "r": +0.004, "p": +0.004, "q": +0.004,
    # tighten around round shapes a little
    "o": -0.002, "O": -0.009,
    # slender shapes
    "i": -0.005, "l": -0.006, "I": -0.006, "1": -0.006, "|": -0.006,
    "t": -0.004, "f": -0.003, "j": -0.003,
    # punctuation nips
    ":": -0.003, ";": -0.003
}

# -------------------- Helpers ------------------------
def download_base(name: str) -> str:
    url = URL_BASE + name
    dest = os.path.join(BASECACHE, name)
    if not os.path.exists(dest):
        print(f"→ Downloading {name}")
        r = requests.get(url); r.raise_for_status()
        with open(dest, "wb") as f: f.write(r.content)
    else:
        print(f"✓ Found base {name}")
    return dest

def get_base_letter(ch: str) -> str:
    """Return a Latin base letter for a char, e.g., 'á' -> 'a', 'Ç' -> 'c'; else original."""
    decomp = unicodedata.normalize("NFD", ch)
    for c in decomp:
        # use letter category and Latin range hint
        if c.isalpha():
            return c
    return ch

def set_coords(glyph, coords, endPts, flags):
    # keep flags length in sync to avoid pen errors
    if len(coords) != len(flags):
        if len(coords) > len(flags):
            flags = list(flags) + [flags[-1]] * (len(coords) - len(flags))
        else:
            flags = list(flags)[:len(coords)]
    glyph.coordinates = GlyphCoordinates(coords)
    glyph.endPtsOfContours = endPts
    glyph.flags = flags

# ----------------- Transformations -------------------
def apply_optical_anchor(tt: TTFont, entry_band: float, global_strength: float):
    """Entry anchoring for all Latin letters (upper+lower, incl. diacritics)."""
    if global_strength <= 0: 
        print("✓ Anchoring: off")
        return

    glyf = tt["glyf"]; cmap = tt.getBestCmap() or {}
    affected = 0

    for code, gname in cmap.items():
        ch = chr(code)
        # quick Latin filter (Basic + Supplement + Extended-A/B rough gate)
        if not ('\u0000' <= ch <= '\u024F') and not ('\u1E00' <= ch <= '\u1EFF'):
            continue

        base = get_base_letter(ch)
        strength_key = None
        if base in ANCHOR_LC: strength_key = base
        elif base in ANCHOR_UC: strength_key = base

        if not strength_key: 
            continue
        g = glyf[gname]
        if not hasattr(g, "getCoordinates"): 
            continue

        try:
            coords, endPts, flags = g.getCoordinates(glyf)
        except Exception:
            continue
        if not coords:
            continue

        # choose base strength table
        per_letter = ANCHOR_LC.get(strength_key, ANCHOR_UC.get(strength_key, 0.0))
        s = per_letter * global_strength
        if s <= 0:
            continue

        xs = [x for x,_ in coords]
        x_min, x_max = min(xs), max(xs)
        width = max(1, x_max - x_min)

        newc = []
        band = entry_band
        for x, y in coords:
            ratio = (x - x_min) / width  # 0=left, 1=right
            if ratio <= band:
                t = 1.0 - (ratio / band)     # 1→0 across band
                shift = s * t * width
                newc.append((int(x - shift), int(y)))
            else:
                newc.append((int(x), int(y)))
        set_coords(g, newc, endPts, flags)
        affected += 1

    print(f"✓ Anchoring: {affected} glyphs (band={entry_band:.2f}, global={global_strength:.2f})")

def raise_xheight(tt: TTFont, factor: float):
    if abs(factor - 1.0) < 1e-3:
        print("✓ x-height: ×1.00 (no change)")
        return
    glyf = tt["glyf"]; cmap = tt.getBestCmap() or {}
    n = 0
    for code, gname in cmap.items():
        ch = chr(code)
        # lowercase only
        if not ch.islower(): 
            continue
        g = glyf[gname]
        if not hasattr(g, "getCoordinates"): 
            continue
        coords, endPts, flags = g.getCoordinates(glyf)
        newc = [(x, int(y*factor)) for x, y in coords]
        set_coords(g, newc, endPts, flags)
        n += 1
    print(f"✓ x-height: ×{factor:.2f} ({n} glyphs)")

def apply_comfort_spacing(tt: TTFont, letter_factor: float, word_factor: float):
    """Advance width scaling only; keep LSB unchanged so outlines don't drift."""
    hmtx = tt["hmtx"].metrics
    for gname, (adv, lsb) in list(hmtx.items()):
        if gname == "space": 
            continue
        hmtx[gname] = (max(1, int(round(adv * letter_factor))), lsb)
    if "space" in hmtx:
        adv, lsb = hmtx["space"]
        hmtx["space"] = (max(1, int(round(adv * word_factor))), lsb)
    print(f"✓ Comfort spacing: letters ×{letter_factor:.2f}, word ×{word_factor:.2f}")

def apply_micro_spacing(tt: TTFont, level: float = 1.0):
    """Per-letter micro nudges in EM; advance width only."""
    if level <= 0: 
        print("✓ Micro-spacing: off")
        return
    upm = tt["head"].unitsPerEm
    cmap = tt.getBestCmap() or {}
    hmtx = tt["hmtx"].metrics
    n = 0
    for code, gname in cmap.items():
        ch = chr(code)
        base = get_base_letter(ch)
        key = None
        if ch in MICRO_SPACING_EM: key = ch
        elif base in MICRO_SPACING_EM: key = base
        if key is None: 
            continue
        du = int(round(MICRO_SPACING_EM[key] * level * upm))
        if gname in hmtx:
            adv, lsb = hmtx[gname]
            hmtx[gname] = (max(1, adv + du), lsb)
            n += 1
    print(f"✓ Micro-spacing: applied to {n} glyphs (level={level:.2f})")

def set_naming(tt: TTFont, family: str, style: str, weight: int):
    nm = tt["name"]; full = f"{family} {style}"
    def setn(i, s): nm.setName(s, i, 3, 1, 0x409)
    setn(1, family); setn(2, style); setn(4, full); setn(5, f"{full} — {VERSION_STR}"); setn(6, full.replace(" ",""))
    if "OS/2" in tt: tt["OS/2"].usWeightClass = weight

# -------------------- Build core ---------------------
def build_one(src_path, out_path, family, style, weight, anchor, xh, let_sp, word_sp, micro_level):
    tt = TTFont(src_path)
    apply_optical_anchor(tt, ENTRY_BAND, anchor)
    raise_xheight(tt, xh)
    apply_comfort_spacing(tt, let_sp, word_sp)
    apply_micro_spacing(tt, micro_level)
    set_naming(tt, family, style, weight)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tt.save(out_path)
    print(f"→ Saved {out_path}")

def compress_to_woff2(ttf_path: str):
    """
    Robust WOFF2 conversion:
      1) Try capturing STDOUT into /fonts/web/*.woff2
      2) If the binary writes *.ttf.woff2 next to the input, move/rename it
    """
    woff2_bin = os.environ.get("WOFF2_BIN", "/opt/homebrew/bin/woff2_compress")
    if not os.path.exists(woff2_bin):
        print("⚠ woff2_compress not found; install with: brew install woff2 (or set WOFF2_BIN)")
        return

    ttf_dir  = os.path.dirname(ttf_path)
    ttf_base = os.path.basename(ttf_path)
    out_woff = os.path.join(OUT_WEB, ttf_base.replace(".ttf", ".woff2"))
    os.makedirs(os.path.dirname(out_woff), exist_ok=True)

    # Attempt 1: capture STDOUT
    try:
        with open(out_woff, "wb") as f_out:
            subprocess.run([woff2_bin, ttf_base], cwd=ttf_dir, check=True, stdout=f_out)
        if os.path.getsize(out_woff) > 0:
            print(f"✓ Webfont: {out_woff}")
            return
    except subprocess.CalledProcessError as e:
        print(f"⚠ woff2_compress failed (stdout mode) on {ttf_base}: {e}")
    except Exception as e:
        # fall through to attempt 2
        pass

    # Attempt 2: look for *.ttf.woff2 next to TTF, or in cwd
    generated_here = os.path.join(ttf_dir, ttf_base + ".woff2")
    generated_cwd  = os.path.join(os.getcwd(), ttf_base + ".woff2")
    if os.path.exists(generated_here):
        os.replace(generated_here, out_woff)
        print(f"✓ Webfont: {out_woff}")
    elif os.path.exists(generated_cwd):
        os.replace(generated_cwd, out_woff)
        print(f"✓ Webfont (from cwd): {out_woff}")
    else:
        print(f"⚠ woff2 output not found for {ttf_base}")

# ---------------------- Main -------------------------
def main():
    # fetch base fonts
    base_paths = {sty: download_base(fname) for sty, fname in BASES.items()}

    for family, (weights, anchor_mult, xh, let_sp, word_sp, micro_level) in FAMILIES.items():
        print(f"\n=== Building {family} ===")
        for style, weight in weights.items():
            src = base_paths[style]
            out_ttf = os.path.join(OUT_TTF, f"{family.replace(' ','')}-{style}.ttf")
            build_one(src, out_ttf, family, style, weight, anchor_mult, xh, let_sp, word_sp, micro_level)
            compress_to_woff2(out_ttf)

    print("\n✅ Done: TTFs in fonts/ttf, WOFF2 in fonts/web")

if __name__ == "__main__":
    main()

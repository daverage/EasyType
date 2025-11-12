#!/usr/bin/env python3
"""
EasyType Font Builder (multilingual final)
==========================================
Builds:
  • fonts/ttf/*.ttf  — hinted and platform-safe
  • fonts/web/*.woff2 — compressed for web

Supports:
  Latin + Latin-Extended + Greek + Cyrillic

Requires:
  pip install fonttools requests
Optional:
  brew install woff2 ttfautohint
"""

import fractions
import os, sys, subprocess, unicodedata, requests, shutil
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.pens.ttGlyphPen import TTGlyphPen

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

VERSION_DISPLAY = "1.0.2"
VERSION_DECIMAL = "1.002"
VERSION_STR = f"EasyType v{VERSION_DISPLAY}"

# -------------------- Families -----------------------
FAMILY_DISPLAY = {
    "EasyType Sans": "Easy Type Sans",
    "EasyType Focus": "Easy Type Focus",
    "EasyType Dyslexic": "Easy Type Dyslexic",
}

FAMILIES = {
    "EasyType Sans": (
        {
            "Regular": (400, "Regular"),
            "Italic": (400, "Italic"),
            "Bold": (700, "Bold"),
            "BoldItalic": (700, "Bold Italic"),
        },
        0.25,
        1.02,
        1.06,
        1.12,
        0.8,
    ),
    "EasyType Focus": (
        {
            "Regular": (400, "Regular"),
            "Italic": (400, "Italic"),
            "Bold": (700, "Bold"),
            "BoldItalic": (700, "Bold Italic"),
        },
        0.40,
        1.06,
        1.14,
        1.24,
        1.0,
    ),
    "EasyType Dyslexic": (
        {
            "Regular": (400, "Regular"),
            "Italic": (400, "Italic"),
            "Bold": (700, "Bold"),
            "BoldItalic": (700, "Bold Italic"),
        },
        0.55,
        1.10,
        1.22,
        1.32,
        1.0,
    ),
}

ENTRY_BAND = 0.18
FAMILY_METRICS = {}
WIN_ASCENT_MIN = 1084
WIN_DESCENT_MIN = 427

# -------------------- Anchoring tables -----------------
ANCHOR_LC = {
    "a":0.28,"b":0.16,"c":0.34,"d":0.22,"e":0.32,"f":0.12,"g":0.26,"h":0.16,"i":0.10,"j":0.11,"k":0.13,"l":0.10,
    "m":0.20,"n":0.18,"o":0.32,"p":0.22,"q":0.22,"r":0.18,"s":0.24,"t":0.16,"u":0.22,"v":0.14,"w":0.16,"x":0.12,"y":0.16,"z":0.12
}
ANCHOR_UC = {
    "A":0.08,"B":0.20,"C":0.22,"D":0.20,"E":0.22,"F":0.20,"G":0.22,"H":0.18,"I":0.00,"J":0.20,"K":0.20,"L":0.22,
    "M":0.20,"N":0.20,"O":0.22,"P":0.20,"Q":0.22,"R":0.20,"S":0.22,"T":0.18,"U":0.20,"V":0.16,"W":0.18,"X":0.14,"Y":0.16,"Z":0.14
}

# Greek + Cyrillic → Latin anchor analogues
ANCHOR_BASE_MAP = {
    "Α":"A","Β":"B","Γ":"C","Δ":"A","Ε":"E","Ζ":"Z","Η":"H","Θ":"O","Ι":"I","Κ":"K","Λ":"A","Μ":"M",
    "Ν":"N","Ξ":"E","Ο":"O","Π":"H","Ρ":"P","Σ":"S","Τ":"T","Υ":"Y","Φ":"F","Χ":"X","Ψ":"Y","Ω":"O",
    "α":"a","β":"b","γ":"c","δ":"a","ε":"e","ζ":"z","η":"h","θ":"o","ι":"i","κ":"k","λ":"a","μ":"m",
    "ν":"n","ξ":"e","ο":"o","π":"h","ρ":"p","σ":"s","τ":"t","υ":"u","φ":"f","χ":"x","ψ":"y","ω":"o",
    "А":"A","В":"B","С":"C","Е":"E","Н":"H","К":"K","М":"M","О":"O","Р":"P","Т":"T","У":"Y","Х":"X",
    "а":"a","в":"b","е":"e","к":"k","м":"m","н":"n","о":"o","р":"p","с":"c","т":"t","у":"y","х":"x",
}

# -------------------- Micro spacing ------------------
MICRO_SPACING_EM = {
    "m":+0.010,"w":+0.009,"M":+0.012,"W":+0.012,"g":+0.008,"G":+0.010,"Q":+0.010,"8":+0.010,"0":+0.006,
    "n":+0.006,"h":+0.006,"u":+0.006,"r":+0.004,"p":+0.004,"q":+0.004,"o":-0.002,"O":-0.009,
    "i":-0.005,"l":-0.006,"I":-0.006,"1":-0.006,"|":-0.006,"t":-0.004,"f":-0.003,"j":-0.003,
    ":":-0.003,";":-0.003
}

# -------------------- Helpers ------------------------
def download_base(name):
    url = URL_BASE + name
    dest = os.path.join(BASECACHE, name)
    if not os.path.exists(dest):
        print(f"→ Downloading {name}")
        r = requests.get(url); r.raise_for_status()
        open(dest,"wb").write(r.content)
    else:
        print(f"✓ Found base {name}")
    return dest

def get_base_letter(ch):
    """Normalize diacritics to base Latin letter."""
    decomp = unicodedata.normalize("NFD", ch)
    for c in decomp:
        if c.isalpha():
            return c
    return ch

def set_coords(glyph, coords, endPts, flags):
    if len(coords)!=len(flags):
        flags=list(flags)+[flags[-1]]*abs(len(coords)-len(flags))
    glyph.coordinates=GlyphCoordinates(coords)
    glyph.endPtsOfContours=endPts
    glyph.flags=flags

def remove_soft_hyphen(tt):
    """Removes the soft-hyphen glyph (U+00AD) and its mapping."""
    cmap = tt.getBestCmap()
    if cmap and 0x00AD in cmap:
        glyph_name = cmap[0x00AD]
        print(f"✓ Removing soft-hyphen (U+00AD, glyph: {glyph_name})")
        for table in tt["cmap"].tables:
            if table.isUnicode() and 0x00AD in table.cmap:
                del table.cmap[0x00AD]

def remove_stat_table(tt):
    """Removes the STAT table if it exists, as it's not needed for static fonts."""
    if "STAT" in tt:
        del tt["STAT"]
        print("✓ Removed STAT table to prevent issues on Windows")

# ----------------- Transformations -------------------
def apply_optical_anchor(tt, entry_band, global_strength):
    glyf=tt["glyf"]; cmap=tt.getBestCmap() or {}; affected=0
    for code,gname in cmap.items():
        ch=chr(code)
        if not (
            ('\u0000'<=ch<='\u024F')
            or ('\u1E00'<=ch<='\u1EFF')
            or ('\u0370'<=ch<='\u03FF')
            or ('\u0400'<=ch<='\u04FF')
        ): continue
        base=get_base_letter(ch)
        if ch in ANCHOR_BASE_MAP:
            base=ANCHOR_BASE_MAP[ch]
        s_key=ANCHOR_LC.get(base) or ANCHOR_UC.get(base)
        if not s_key: continue
        g=glyf[gname]
        if not hasattr(g,"getCoordinates"): continue
        coords,endPts,flags=g.getCoordinates(glyf)
        if not coords: continue
        s=s_key*global_strength
        xs=[x for x,_ in coords]; x_min,x_max=min(xs),max(xs)
        width=max(1,x_max-x_min)
        newc=[]
        for x,y in coords:
            ratio=(x-x_min)/width
            if ratio<=entry_band:
                t=1.0-(ratio/entry_band)
                newc.append((int(x - s*t*width),int(y)))
            else:newc.append((int(x),int(y)))
        set_coords(g,newc,endPts,flags); affected+=1
    print(f"✓ Anchoring: {affected} glyphs (global={global_strength:.2f})")

def raise_xheight(tt,factor):
    if abs(factor-1.0)<1e-3: return
    glyf=tt["glyf"]; cmap=tt.getBestCmap() or {}
    for code,gname in cmap.items():
        ch=chr(code)
        if not ch.islower(): continue
        g=glyf[gname]
        if not hasattr(g,"getCoordinates"): continue
        coords,endPts,flags=g.getCoordinates(glyf)
        coords=[(x,int(y*factor)) for x,y in coords]
        set_coords(g,coords,endPts,flags)
    print(f"✓ x-height scaled ×{factor:.2f}")

def apply_comfort_spacing(tt, letter_factor, word_factor):
    hmtx=tt["hmtx"].metrics
    for gname,(adv,lsb) in list(hmtx.items()):
        if gname=="space": continue
        hmtx[gname]=(max(1,int(round(adv*letter_factor))),lsb)
    if "space" in hmtx:
        adv,lsb=hmtx["space"]; hmtx["space"]=(max(1,int(round(adv*word_factor))),lsb)
    print(f"✓ Spacing: letters×{letter_factor:.2f}, words×{word_factor:.2f}")

def apply_micro_spacing(tt, level):
    if level<=0: return
    upm=tt["head"].unitsPerEm; cmap=tt.getBestCmap() or {}; hmtx=tt["hmtx"].metrics
    n=0
    for code,gname in cmap.items():
        ch=chr(code); base=get_base_letter(ch)
        key=MICRO_SPACING_EM.get(ch) or MICRO_SPACING_EM.get(base)
        if not key: continue
        du=int(round(key*level*upm))
        if gname in hmtx:
            adv,lsb=hmtx[gname]; hmtx[gname]=(max(1,adv+du),lsb); n+=1
    print(f"✓ Micro-spacing applied to {n} glyphs")

def set_naming(tt, family, style_key, style_label, weight):
    """Sets font naming to be compliant with Google Fonts standards."""
    nm = tt["name"]
    family_label = FAMILY_DISPLAY.get(family, family)
    full = f"{family_label} {style_label}"
    ps_name = f"{family.replace(' ', '')}-{style_key}"
    def setn(i, s): nm.setName(s, i, 3, 1, 0x409)

    nm.names = [n for n in nm.names if n.nameID not in [1, 2, 4, 5, 6, 16]]
    setn(1, family_label)
    nm.removeNames(nameID=16)
    setn(2, style_label)
    setn(4, full)
    setn(5, f"Version {VERSION_DECIMAL}")
    setn(6, ps_name)

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
        os2.fsSelection &= ~((1<<0) | (1<<5) | (1<<6))
        os2.fsSelection |= selection
        os2.fsSelection |= (1 << 7)

    if "head" in tt:
        tt["head"].fontRevision = float(fractions.Fraction(VERSION_DECIMAL))
    print(f"✓ Set naming for {ps_name}")


def ensure_win_metrics(tt):
    head = tt["head"]
    os2 = tt["OS/2"]
    if os2.usWinAscent < head.yMax:
        os2.usWinAscent = max(head.yMax, WIN_ASCENT_MIN)
    else:
        os2.usWinAscent = max(os2.usWinAscent, WIN_ASCENT_MIN)
    descent = abs(head.yMin)
    if os2.usWinDescent < descent:
        os2.usWinDescent = max(descent, WIN_DESCENT_MIN)
    else:
        os2.usWinDescent = max(os2.usWinDescent, WIN_DESCENT_MIN)


def ensure_minus_glyph(tt):
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
        coords, endPts, flags = source_glyph.getCoordinates(glyf)
        new_glyph.coordinates = GlyphCoordinates(coords)
        new_glyph.endPtsOfContours = list(endPts)
        new_glyph.flags = list(flags)
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


def sync_space_nbspace(tt):
    hmtx = tt["hmtx"].metrics
    if "space" in hmtx and "nbspace" in hmtx:
        adv, lsb = hmtx["space"]
        hmtx["nbspace"] = (adv, lsb)


def sync_vertical_metrics(tt, reference=None):
    if reference is None:
        return
    if "hhea" in tt and "hhea" in reference:
        tt["hhea"].ascent = reference["hhea"].ascent
        tt["hhea"].descent = reference["hhea"].descent
        tt["hhea"].lineGap = reference["hhea"].lineGap
    if "OS/2" in tt and "OS/2" in reference:
        src = reference["OS/2"]
        dst = tt["OS/2"]
        dst.sTypoAscender = src.sTypoAscender
        dst.sTypoDescender = src.sTypoDescender
        dst.sTypoLineGap = src.sTypoLineGap
        dst.usWinAscent = src.usWinAscent
        dst.usWinDescent = src.usWinDescent


def sanitize_gdef_marks(tt):
    if "GDEF" not in tt:
        return
    gdef = tt["GDEF"].table
    glyph_class = getattr(gdef, "GlyphClassDef", None)
    if not glyph_class or not glyph_class.classDefs:
        return
    hmtx = tt["hmtx"].metrics
    for glyph, cls in list(glyph_class.classDefs.items()):
        if cls == 3 and glyph in hmtx and hmtx[glyph][0] != 0:
            glyph_class.classDefs[glyph] = 1


def clone_glyph(tt, src_name, dst_name, target_code):
    glyf = tt["glyf"]
    hmtx = tt["hmtx"].metrics
    glyph_order = list(tt.getGlyphOrder())
    if dst_name in glyf or src_name not in glyf:
        return
    src = glyf[src_name]
    new_g = src.__class__()
    new_g.numberOfContours = src.numberOfContours
    if src.numberOfContours >= 0:
        coords, endPts, flags = src.getCoordinates(tt["glyf"])
        new_g.coordinates = GlyphCoordinates(coords)
        new_g.endPtsOfContours = list(endPts)
        new_g.flags = list(flags)
    else:
        new_g.components = list(src.components)
        if hasattr(src, "program"):
            new_g.program = src.program
    glyf[dst_name] = new_g
    glyph_order.append(dst_name)
    tt.setGlyphOrder(glyph_order)
    if src_name in hmtx:
        hmtx[dst_name] = hmtx[src_name]
    for table in tt["cmap"].tables:
        if table.isUnicode():
            table.cmap[target_code] = dst_name


def ensure_case_pairs(tt):
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


def flatten_composites(tt):
    glyf_table = tt["glyf"]
    for glyph_name in tt.getGlyphOrder():
        glyph = glyf_table[glyph_name]
        if glyph.isComposite():
            pen = TTGlyphPen(glyf_table)
            glyph.draw(pen, glyf_table)
            glyf_table[glyph_name] = pen.glyph()


def capture_metrics_snapshot(tt):
    snapshot = {}
    if "hhea" in tt:
        hhea = tt["hhea"]
        snapshot["hhea"] = { "ascent": hhea.ascent, "descent": hhea.descent, "lineGap": hhea.lineGap }
    if "OS/2" in tt:
        os2 = tt["OS/2"]
        snapshot["OS/2"] = {
            "sTypoAscender": os2.sTypoAscender, "sTypoDescender": os2.sTypoDescender,
            "sTypoLineGap": os2.sTypoLineGap, "usWinAscent": os2.usWinAscent,
            "usWinDescent": os2.usWinDescent
        }
    return snapshot


def apply_metrics_snapshot(tt, family):
    snapshot = FAMILY_METRICS.get(family)
    if not snapshot: return
    if "hhea" in tt and "hhea" in snapshot:
        hhea = tt["hhea"]; data = snapshot["hhea"]
        hhea.ascent, hhea.descent, hhea.lineGap = data["ascent"], data["descent"], data["lineGap"]
    if "OS/2" in tt and "OS/2" in snapshot:
        os2 = tt["OS/2"]; data = snapshot["OS/2"]
        os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = data["sTypoAscender"], data["sTypoDescender"], data["sTypoLineGap"]
        os2.usWinAscent, os2.usWinDescent = data["usWinAscent"], data["usWinDescent"]


def recompute_xavg(tt):
    os2 = tt["OS/2"]
    metrics = tt["hmtx"].metrics
    total, count = 0, 0
    for adv, _ in metrics.values():
        if adv > 0:
            total += adv; count += 1
    if count == 0: return
    os2.xAvgCharWidth = int(round(total / count))


def set_head_flags(tt):
    tt["head"].flags |= 1 << 3


def adjust_metrics_after_hint(font_path):
    tt = TTFont(font_path)
    ensure_win_metrics(tt)
    recompute_xavg(tt)
    set_head_flags(tt)
    tt.save(font_path)


# ----------------- Hinting ---------------------------
def auto_hint(in_path,out_path):
    bin_path=shutil.which("ttfautohint")
    if not bin_path:
        print("⚠ ttfautohint not found; skipping hinting")
        return False
    subprocess.run([bin_path,"--windows-compatibility","--symbol","--no-info",in_path,out_path],check=False)
    print(f"✓ Hinting applied → {out_path}")
    return True

# ----------------- Build & Compress -------------------
def build_one(
    src_path, out_path, family, style_key, style_label, weight,
    anchor, xh, let_sp, word_sp, micro_level, reference_snapshot=None
):
    tt = TTFont(src_path)
    
    apply_optical_anchor(tt, ENTRY_BAND, anchor)
    raise_xheight(tt, xh)
    apply_comfort_spacing(tt, let_sp, word_sp)
    apply_micro_spacing(tt, micro_level)

    set_naming(tt, family, style_key, style_label, weight)
    ensure_minus_glyph(tt)
    remove_soft_hyphen(tt)
    sync_space_nbspace(tt)
    ensure_case_pairs(tt)

    flatten_composites(tt)

    sanitize_gdef_marks(tt)
    remove_stat_table(tt)

    if reference_snapshot:
        apply_metrics_snapshot(tt, family)

    tmp = out_path.replace(".ttf", "-tmp.ttf")
    tt.save(tmp)
    if not auto_hint(tmp, out_path):
        shutil.move(tmp, out_path)
    else:
        os.remove(tmp)
    
    adjust_metrics_after_hint(out_path)
    print(f"→ Saved {out_path}")

def compress_to_woff2(ttf_path):
    possible_paths = [
        os.environ.get("WOFF2_BIN"), shutil.which("woff2_compress"),
        "/opt/homebrew/bin/woff2_compress", "/usr/local/bin/woff2_compress"
    ]
    woff2_bin = next((p for p in possible_paths if p and os.path.exists(p)), None)
    if not woff2_bin:
        print("⚠ woff2_compress not found; skipping webfont")
        return

    ttf_dir = os.path.dirname(ttf_path)
    ttf_base = os.path.basename(ttf_path)
    out_woff = os.path.join(OUT_WEB, ttf_base.replace(".ttf", ".woff2"))
    os.makedirs(os.path.dirname(out_woff), exist_ok=True)
    generated_woff_path = os.path.join(ttf_dir, ttf_base.replace(".ttf", ".woff2"))

    print(f"Processing {ttf_base} → {out_woff}")
    try:
        subprocess.run([woff2_bin, ttf_base], cwd=ttf_dir, check=True, capture_output=True)
        shutil.move(generated_woff_path, out_woff)
        print(f"✓ Webfont: {out_woff}")
    except subprocess.CalledProcessError as e:
        print(f"⚠ woff2_compress failed on {ttf_base}: {e.stderr.decode()}")
    except FileNotFoundError:
        print(f"⚠ Could not locate generated .woff2 output for {ttf_base}")


# ---------------------- Main -------------------------
def main():
    base_paths = {sty: download_base(fname) for sty, fname in BASES.items()}
    for family, (weights, anchor, xh, let_sp, word_sp, micro_level) in FAMILIES.items():
        print(f"\n=== Building {family} ===")
        for style, (weight, style_label) in weights.items():
            src = base_paths[style]
            out_ttf = os.path.join(OUT_TTF, f"{family.replace(' ', '')}-{style}.ttf")
            build_one(
                src, out_ttf, family, style, style_label, weight,
                anchor, xh, let_sp, word_sp, micro_level,
                reference_snapshot=FAMILY_METRICS.get(family),
            )
            if style_label.lower() == "regular":
                FAMILY_METRICS[family] = capture_metrics_snapshot(TTFont(out_ttf))
            compress_to_woff2(out_ttf)
    print("\n✅ Done: hinted TTFs in fonts/ttf, WOFF2 in fonts/web")

if __name__ == "__main__":
    main()

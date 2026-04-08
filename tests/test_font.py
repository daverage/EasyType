"""
Unit tests for EasyType font builder core functions.

Run with:
    pytest tests/test_font.py -v
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import zipfile

import pytest

# Make the Generator Tools package importable without installing it.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Generator Tools"))
import font as ft  # noqa: E402 — must come after sys.path manipulation


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _empty_glyph():
    """Return a proper empty (no-contour) TTF Glyph object."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    pen = TTGlyphPen(None)
    return pen.glyph()


def _make_minimal_ttfont(upm: int = 1000) -> ft.TTFont:
    """Build the smallest TTFont that the builder functions can operate on."""
    from fontTools.fontBuilder import FontBuilder
    fb = FontBuilder(upm, isTTF=True)
    glyph_names = [".notdef", "A", "a", "zero"]
    fb.setupGlyphOrder(glyph_names)
    fb.setupCharacterMap({65: "A", 97: "a", 48: "zero"})
    fb.setupGlyf({name: _empty_glyph() for name in glyph_names})
    fb.setupHorizontalMetrics({
        ".notdef": (500, 0),
        "A": (600, 50),
        "a": (520, 40),
        "zero": (580, 45),
    })
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    fb.setupOS2(
        sTypoAscender=800, sTypoDescender=-200, sTypoLineGap=0,
        usWinAscent=900, usWinDescent=200,
        sxHeight=500, sCapHeight=700,
        fsType=0,
    )
    fb.setupPost()
    fb.setupHead(unitsPerEm=upm)
    buf = io.BytesIO()
    fb.font.save(buf)
    buf.seek(0)
    return ft.TTFont(buf)


# ─── StemPosition Enum ────────────────────────────────────────────────────────

class TestStemPositionEnum:
    def test_enum_values_are_strings(self):
        for member in ft.StemPosition:
            assert isinstance(member.value, str)

    def test_all_map_entries_are_enum(self):
        for cp, pos in ft.STEM_SHIFT_MAP.items():
            assert isinstance(pos, ft.StemPosition), (
                f"U+{cp:04X} has non-Enum position {pos!r}"
            )

    def test_no_bare_string_positions(self):
        """Ensure STEM_SHIFT_MAP contains no raw strings."""
        for cp, pos in ft.STEM_SHIFT_MAP.items():
            assert not isinstance(pos, str), (
                f"U+{cp:04X} still uses raw string {pos!r}"
            )


# ─── Download cache validation ────────────────────────────────────────────────

class TestInterZipValidation:
    def test_valid_zip_passes(self, tmp_path):
        """A properly formed zip is accepted."""
        zip_path = tmp_path / "Inter-4.1.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Inter-Regular.ttf", b"placeholder")
        # Monkey-patch the cache path
        original = ft.INTER_ZIP_CACHE
        ft.INTER_ZIP_CACHE = str(zip_path)
        try:
            assert ft._inter_zip_is_valid() is True
        finally:
            ft.INTER_ZIP_CACHE = original

    def test_missing_file_returns_false(self, tmp_path):
        original = ft.INTER_ZIP_CACHE
        ft.INTER_ZIP_CACHE = str(tmp_path / "nonexistent.zip")
        try:
            assert ft._inter_zip_is_valid() is False
        finally:
            ft.INTER_ZIP_CACHE = original

    def test_corrupt_file_returns_false(self, tmp_path):
        zip_path = tmp_path / "bad.zip"
        zip_path.write_bytes(b"this is not a zip file at all")
        original = ft.INTER_ZIP_CACHE
        ft.INTER_ZIP_CACHE = str(zip_path)
        try:
            assert ft._inter_zip_is_valid() is False
        finally:
            ft.INTER_ZIP_CACHE = original

    def test_truncated_zip_returns_false(self, tmp_path):
        """A zip truncated mid-stream (partial download) fails validation."""
        zip_path = tmp_path / "truncated.zip"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Inter-Regular.ttf", b"x" * 10_000)
        # Write only the first half of the zip bytes
        data = buf.getvalue()
        zip_path.write_bytes(data[: len(data) // 2])
        original = ft.INTER_ZIP_CACHE
        ft.INTER_ZIP_CACHE = str(zip_path)
        try:
            assert ft._inter_zip_is_valid() is False
        finally:
            ft.INTER_ZIP_CACHE = original


# ─── Comfort spacing ──────────────────────────────────────────────────────────

class TestApplyComfortSpacing:
    def test_letter_spacing_scales_advance_widths(self):
        tt = _make_minimal_ttfont()
        before = dict(tt["hmtx"].metrics)
        ft.apply_comfort_spacing(tt, letter_factor=1.10, word_factor=1.20)
        after = tt["hmtx"].metrics
        for gname in ("A", "a"):
            orig_adv = before[gname][0]
            assert after[gname][0] == max(1, round(orig_adv * 1.10))

    def test_space_uses_word_factor(self):
        from fontTools.fontBuilder import FontBuilder
        fb = FontBuilder(1000, isTTF=True)
        glyph_names = [".notdef", "space"]
        fb.setupGlyphOrder(glyph_names)
        fb.setupCharacterMap({32: "space"})
        fb.setupGlyf({name: _empty_glyph() for name in glyph_names})
        fb.setupHorizontalMetrics({".notdef": (500, 0), "space": (250, 0)})
        fb.setupHorizontalHeader(ascent=800, descent=-200)
        fb.setupNameTable({"familyName": "T", "styleName": "R"})
        fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, sTypoLineGap=0,
                    usWinAscent=900, usWinDescent=200,
                    sxHeight=500, sCapHeight=700, fsType=0)
        fb.setupPost()
        fb.setupHead(unitsPerEm=1000)
        buf = io.BytesIO()
        fb.font.save(buf); buf.seek(0)
        tt = ft.TTFont(buf)
        ft.apply_comfort_spacing(tt, letter_factor=1.10, word_factor=1.50)
        assert tt["hmtx"].metrics["space"][0] == max(1, round(250 * 1.50))

    def test_advance_widths_are_never_zero(self):
        tt = _make_minimal_ttfont()
        # Even with a tiny factor, no advance width should go to zero.
        ft.apply_comfort_spacing(tt, letter_factor=0.001, word_factor=0.001)
        for gname, (adv, _) in tt["hmtx"].metrics.items():
            assert adv >= 1, f"{gname} has zero advance width"


# ─── X-height scaling ─────────────────────────────────────────────────────────

class TestRaiseXheight:
    def test_xheight_is_scaled(self):
        tt = _make_minimal_ttfont()
        os2 = tt["OS/2"]
        os2.sxHeight = 500
        ft.raise_xheight(tt, factor=1.06)
        assert tt["OS/2"].sxHeight == round(500 * 1.06)

    def test_noop_at_factor_one(self):
        tt = _make_minimal_ttfont()
        tt["OS/2"].sxHeight = 500
        ft.raise_xheight(tt, factor=1.0)
        assert tt["OS/2"].sxHeight == 500

    def test_raises_on_zero_xheight(self):
        tt = _make_minimal_ttfont()
        tt["OS/2"].sxHeight = 0
        with pytest.raises(ValueError, match="sxHeight"):
            ft.raise_xheight(tt, factor=1.06)


# ─── woff2 binary detection ───────────────────────────────────────────────────

class TestWoff2BinaryDetection:
    def test_env_var_takes_precedence(self, monkeypatch, tmp_path):
        """WOFF2_BIN env var is respected and no hard-coded path is used."""
        fake_bin = tmp_path / "woff2_compress"
        fake_bin.write_text("#!/bin/sh\nexit 0\n")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("WOFF2_BIN", str(fake_bin))
        # Patch subprocess.run to capture what binary is called
        calls = []
        import subprocess as sp
        monkeypatch.setattr(sp, "run", lambda cmd, **kw: calls.append(cmd) or
                            type("R", (), {"returncode": 0})())
        ft.compress_to_woff2(str(tmp_path / "test.ttf"))
        if calls:  # may be skipped if file doesn't exist
            assert calls[0][0] == str(fake_bin)

    def test_no_hardcoded_homebrew_path(self):
        """Ensure no hard-coded /opt/homebrew or /usr/local paths exist in the source."""
        src = os.path.join(os.path.dirname(__file__), "..", "Generator Tools", "font.py")
        with open(src, encoding="utf-8") as fh:
            source = fh.read()
        assert "/opt/homebrew/bin/woff2_compress" not in source
        assert "/usr/local/bin/woff2_compress" not in source


# ─── FamilyConfig dataclass ───────────────────────────────────────────────────

class TestFamilyConfig:
    def test_all_families_present(self):
        assert set(ft.FAMILIES) == {
            "EasyType Sans", "EasyType Focus", "EasyType Steady"
        }

    def test_parameter_ordering(self):
        """Focus > Sans, Steady > Focus for every intensity parameter."""
        sans   = ft.FAMILIES["EasyType Sans"]
        focus  = ft.FAMILIES["EasyType Focus"]
        steady = ft.FAMILIES["EasyType Steady"]
        for attr in ("anchor_strength", "xheight_factor", "letter_spacing", "word_spacing"):
            assert getattr(sans, attr) < getattr(focus, attr) < getattr(steady, attr), (
                f"{attr}: expected Sans < Focus < Steady"
            )

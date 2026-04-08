# EasyType Fonts

**Neuro-inclusive typefaces for calmer, clearer reading.**  
EasyType is an open font family designed for readers with ADHD, dyslexia, and other attention-related differences. Built on typographic and neuroscience research, it blends subtle optical anchoring, balanced spacing, and improved letter rhythm to make text feel easier to read - without sacrificing design quality.

I live with both ADHD and dyslexia, and EasyType started as a personal experiment to make long reading sessions less tiring. Every decision in this project is shaped by that need for calmer, more efficient reading.

---

## ✳️ Font Families

| Font | Description |
|------|--------------|
| **EasyType Sans** | Neutral rhythm and mild anchoring for everyday interfaces and long-form text. |
| **EasyType Focus** | Wider letter and word spacing to support attentional flow and reduce visual crowding. |
| **EasyType Steady** | Higher x-height, stronger entry anchors, and open counters for maximum clarity under reading pressure. |

Each family includes:
- Regular, Italic, Bold, and Bold Italic styles
- Full Latin, Greek, and Cyrillic character support (including accented and extended letters)
- `.ttf` and `.woff2` versions ready for desktop and web use

---

## 🧠 Why EasyType was built

Traditional fonts are designed for visual uniformity - not for how the eye and brain process language. Research in cognitive science and perceptual psychology shows that subtle cues can reduce eye strain, improve word recognition, and enhance reading rhythm.

As someone managing ADHD and dyslexia, I felt the lack of those cues daily. The design brief was simple: build a type family that helps my own eyes stay anchored and focused first, then open-source it for everyone else who needs the same support.

EasyType implements those cues directly in the letterforms:

- **Entry Anchoring** - Subtle optical shifts on entry strokes create a consistent fixation point at the start of each word, supporting eye tracking and reducing regressions.

- **Raised x-Height** - Taller lowercase letters improve legibility and recognition speed, particularly at smaller sizes.

- **Comfort & Micro Spacing** - Letter and word spacing are increased just enough to reduce crowding, with per-glyph micro-tuning for smoother reading rhythm.

- **Stem Disambiguation** - Key letter pairs that cause rotational confusion in dyslexia (`b/d`, `p/q`) are given subtle stem-entry differences. A small shoulder widening at the stem top of `b` and descender tips of `p` and `q` breaks the mirror symmetry between these pairs without altering the overall character of the letterform.

- **Character Disambiguation** - Inter's built-in disambiguation alternates are baked into the default glyph set. The lowercase `l` has a curved foot, `I` (capital i) has serifs, and `0` (zero) is slashed - making them unambiguous from `1`, `|`, and `O` at any size. No CSS required.

---

## 🧩 Research Background

EasyType draws on findings from visual cognition and reading science:

- Pelli, D.G. & Tillman, K.A. (2008). *The uncrowded window of object recognition.* *Nature Neuroscience, 11*(10).
- Rayner, K. (1998). *Eye movements in reading and information processing.* *Psychological Bulletin, 124*(3).
- Spinelli, D. et al. (2002). *Crowding effects on word recognition in dyslexia.* *Cortex, 38*(2).
- Le Loi, J. & Whitney, C. (2016). *Optimal inter-letter spacing for reading.* *Vision Research, 121.*
- Galliussi, J. et al. (2020). *Inter-letter spacing, inter-word spacing, and font with dyslexia-friendly features.* *Annals of Dyslexia, 70*(1).
- Kuster, S.M. et al. (2018). *Dyslexie font does not benefit reading in children with or without dyslexia.* *Annals of Dyslexia, 68*(1).

> EasyType is not a treatment for ADHD or dyslexia - it is a research-informed design approach that reduces reading effort and improves comfort.

---

## 🔬 Accessibility and Design Philosophy

- Designed to support **attention anchoring**, **saccadic rhythm**, and **crowding reduction**.
- Key confusable letter pairs (`b/d`, `p/q`, `i/l/1`, `0/O`) are disambiguated through both letterform design and OpenType alternate baking.
- Every modification is validated visually and numerically to ensure readability is improved without disrupting typographic proportion.
- The design goal: *clarity without caricature* - fonts that work for everyone, but especially help those who need calmer visual flow.

---

## ⚙️ Building the fonts

You can rebuild all styles locally using Python 3.

### Requirements

```bash
pip install fonttools requests
brew install woff2 ttfautohint    # macOS (both optional but recommended)
```

### Build

```bash
python3 "Generator Tools/font.py"
```

This generates:

```
fonts/
 ├── ttf/
 │   ├── EasyTypeSans-Regular.ttf
 │   ├── EasyTypeSans-Bold.ttf
 │   ├── EasyTypeFocus-Regular.ttf
 │   ├── ...
 └── web/
     ├── EasyTypeSans-Regular.woff2
     └── ...
```

### CLI options

```bash
python3 "Generator Tools/font.py" --family "EasyType Steady"  # one family only
python3 "Generator Tools/font.py" --dry-run                   # validate without output
python3 "Generator Tools/font.py" --no-hint                   # skip ttfautohint
python3 "Generator Tools/font.py" --version
```

### What the build does

1. Downloads Inter v4.1 as the base font (cached after first run)
2. Bakes Inter's disambiguation alternates into the default glyph slots
3. Applies optical entry anchoring across Latin, Greek, and Cyrillic
4. Applies stem disambiguation to `b`, `p`, `q`, and their script equivalents
5. Raises x-height (zone-only - ascenders are translated, not scaled)
6. Applies comfort and micro spacing
7. Hints with `ttfautohint` and compresses to WOFF2
8. Writes a `fonts/build_report.json` with version, metrics, and glyph counts

---

## 🧱 Technical Notes

- **Base font:** Inter v4.1 (rsms/inter), downloaded automatically from GitHub releases. The build caches the zip after first download.
- **Disambiguation:** Inter's `ss02` and `cv05` OpenType alternates are promoted to default glyph positions at build time, so readers benefit without any CSS configuration.
- **X-height scaling:** Only the x-height zone is scaled. Ascenders are shifted by the same absolute delta rather than scaled, preserving the ascender-to-x-height ratio across all three families.
- **Stem disambiguation:** The extreme terminus point of each target stem is shifted laterally. No new points are inserted - the adjacent Bézier handles reshape the curve naturally.
- **Hinting:** `ttfautohint` is run with `--windows-compatibility` for cross-platform rendering. Modified glyphs have their hinting bytecode cleared so ttfautohint re-hints cleanly from the new outlines.
- **WOFF2:** Generated using `woff2_compress`. On Linux or Windows, set a custom binary path:
  ```bash
  export WOFF2_BIN=/usr/local/bin/woff2_compress
  ```
- **Build report:** Each successful build writes `fonts/build_report.json` with version, git commit, per-family glyph counts, and OS/2 metrics.
- **Deterministic:** Re-running the build script with the same inputs produces identical output.

---

## 🌐 Web Embedding & Distribution

### Self-hosting (recommended)

1. **Grab the files**
   - Download the latest release from [GitHub Releases](https://github.com/daverage/EasyType/releases)
   - or install via npm:
     ```bash
     npm install easytype-fonts
     ```
2. Copy `fonts/` and `css/easytype.css` into your project.
3. Reference the stylesheet:
   ```html
   <link rel="stylesheet" href="/assets/fonts/easytype/css/easytype.css">
   ```
4. Use the families like any other web font:
   ```css
   body {
     font-family: 'EasyType Sans', system-ui, sans-serif;
     line-height: 1.6;
     color: #141414;
   }
   ```

### Hosted quick start

For prototypes only - switch to self-hosting before production:

```html
<link rel="stylesheet" href="https://www.marczewski.me.uk/easytype/css/easytype.css?v=1.1.0">
```

---

## 📦 Folder Structure

```
/fonts
  /ttf              → Desktop font files (.ttf)
  /web              → Webfonts (.woff2)
  build_report.json → Build metadata (generated)
/css
  easytype.css      → Web @font-face declarations
  styles.css        → Demo site styling
/assets             → Favicons and web app manifest
/Generator Tools
  font.py           → Font builder script
  build.sh          → Shell wrapper
/demo.html          → Local specimen preview
```

---

## 📄 Licence

**SIL Open Font Licence 1.1**

You may freely:
- Use the fonts for personal or commercial work
- Modify and redistribute them
- Embed them in software or websites

Attribution is appreciated:  
**© 2025 Andrzej Marczewski - EasyType Fonts**

---

## 💬 Learn More

- Website: [marczewski.me.uk/easytype](https://marczewski.me.uk/easytype)
- GitHub: [github.com/daverage/EasyType](https://github.com/daverage/EasyType)
- Creator: [Andrzej Marczewski](https://marczewski.me.uk)

---

*"Good design doesn't demand focus - it invites it."*

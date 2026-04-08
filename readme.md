# EasyType Fonts

**Neuro-inclusive typefaces for calmer, clearer reading.**  
EasyType is an open font family designed for readers with ADHD, dyslexia, and other attention-related differences.  
Built on typographic and neuroscience research, it blends subtle optical anchoring, balanced spacing, and improved rhythm to make text feel easier to read - without sacrificing design quality.

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
- Full Latin character support (including accented and extended letters)  
- `.ttf` and `.woff2` versions ready for desktop and web use

---

## 🧠 Why EasyType was built

Traditional fonts are designed for visual uniformity - not for how the eye and brain process language.  
Research in cognitive science and perceptual psychology shows that subtle cues can reduce eye strain, improve word recognition, and enhance rhythm during reading.

As someone managing ADHD and dyslexia, I felt the lack of those cues daily, so the design brief was simple: build a type family that helps my own eyes stay anchored and focused first, then open-source it for everyone else who needs the same support.

EasyType implements those cues directly in the letterforms:

- **Entry Anchoring:**  
  Slight optical shifts on entry strokes create a consistent fixation point at the start of each word, aiding eye tracking and reducing regressions.
  
- **Raised x-Height:**  
  Taller lowercase letters improve legibility and recognition speed.

- **Comfort & Micro Spacing:**  
  Letter and word spacing are increased just enough to reduce crowding, with micro-tuning per glyph for smoother rhythm.

---

## 🧩 Research Background

EasyType draws on findings from visual cognition and reading science:

- Pelli, D.G. & Tillman, K.A. (2008). *The uncrowded window of object recognition.* *Nature Neuroscience, 11*(10).  
- Rayner, K. (1998). *Eye movements in reading and information processing.* *Psychological Bulletin, 124*(3).  
- Spinelli, D. et al. (2002). *Crowding effects on word recognition in dyslexia.* *Cortex, 38*(2).  
- Le Loi, J. & Whitney, C. (2016). *Optimal inter-letter spacing for reading.* *Vision Research, 121.*

> EasyType is not a treatment for ADHD or dyslexia - it’s a research-informed design approach that helps reduce reading effort and improve comfort.

---

## ⚙️ Building the fonts

You can rebuild all styles locally using Python 3.

### Requirements

```bash
pip install fonttools requests
brew install woff2    # macOS only (optional for webfont compression)
```

### Build

```bash
python3 font.py
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
 
---

## 🌐 Web Embedding & Distribution

### Self-hosting (recommended)
Keeping the font files on your own domain avoids third-party bottlenecks and lets you tune caching headers.

1. **Grab the files**
   - Download the latest zip: `https://www.marczewski.me.uk/easytype/easytypesans.zip`
   - or install via npm:  
     ```bash
     npm install easytype-fonts
     ```
2. Copy `fonts/` and `css/easytype.css` into your project (or import them straight from `node_modules/easytype-fonts`).
3. Reference the stylesheet from your domain:
   ```html
   <link rel="stylesheet" href="/assets/fonts/easytype/css/easytype.css">
   ```
4. Use the families just like any other custom font:
   ```css
   body {
     font-family: 'EasyType Sans', system-ui, sans-serif;
     line-height: 1.6;
     color: #141414;
   }
   ```

### Hosted quick start
Need something fast for prototypes? You can point to the maintained CDN-style copy—just remember to switch to self-hosting before production:

```html
<link rel="stylesheet" href="https://www.marczewski.me.uk/easytype/css/easytype.css?v=1.0.0">
```

---

## 📦 Folder Structure

```
/fonts
  /ttf        → Desktop font files
  /web        → WOFF2 webfonts
/css
  easytype.css → Web import declarations
  styles.css   → Demo site styling
/assets
  easytype-logo.svg
  easytype-favicon.png
  easytype-social.png
/demo.html    → Local specimen preview
/font.py      → Font builder script
```

---

## 🧱 Technical Notes

* The build script automatically downloads the Noto Sans base fonts from Google’s repository.
* Anchoring, spacing, and x-height adjustments are applied via `fontTools` and saved as new TTFs.
* Webfonts (`.woff2`) are generated using `woff2_compress`.
  If you’re on Linux or Windows, set a custom binary path with:

  ```bash
  export WOFF2_BIN=/usr/local/bin/woff2_compress
  ```
* All processing is deterministic - re-running the script will yield identical results.

---

## 🔬 Accessibility and Design Philosophy

* Designed to support **attention anchoring**, **saccadic rhythm**, and **crowding reduction**.
* Every modification was validated visually and numerically for readability without disrupting typographic proportion.
* The design goal: *clarity without caricature* - fonts that work for everyone but especially help those who need calmer visual flow.
* This is the toolkit I wanted for myself as a reader with ADHD and dyslexia, so every refinement is judged by whether it genuinely makes my own reading more efficient.

---

## 📄 Licence

**SIL Open Font Licence 1.1**

You may freely:

* Use the fonts for personal or commercial work
* Modify and redistribute them
* Embed them in software or websites

Attribution is appreciated:
**© 2025 Andrzej Marczewski - EasyType Fonts**

---

## 💬 Learn More

* Website: [https://marczewski.me.uk/easytype](https://marczewski.me.uk/easytype)
* GitHub: [https://github.com/daverage/EasyType](https://github.com/daverage/EasyType)
* Creator: [Andrzej Marczewski](https://marczewski.me.uk)

---

*“Good design doesn’t demand focus - it invites it.”*

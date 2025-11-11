# EasyType | Google Fonts submission

EasyType is a trio of neuro-inclusive sans serif families (Sans, Focus, and Dyslexic) that pair optical anchoring, raised x-height, and comfort spacing to help readers with ADHD, dyslexia, and other attention differences stay calm and focused. These styles were shaped from personal research on rhythm, crowding, and visual anchoring so the fonts feel easy to follow during long-form reading while still delivering refined, contemporary proportions.

## Notable features
- **Entry anchors & raised x-height:** fixed optical offsets and taller lowercase forms provide reliable fixation points and quicker recognition of each word.
- **Comfort spacing:** letter and word spacing are tuned per glyph plus gentle micro-spacing so lines stay open without looking forced.
- **Distinct rhythm per family:** EasyType Sans is the everyday workhorse, Focus adds wider spacing for attentional flow, and Dyslexic maximizes openness for strained reading moments.
- **Inclusive Latin coverage:** latin + latin-extended + greek + cyrillic glyphs are rebuilt from Noto sources with the EasyType adjustments.

## Scripts
Supports: Latin (basic + extended), Greek, Cyrillic.

## Build
### Requirements
1. `pip install fonttools requests`
2. `brew install woff2` *(macOS only, optional for `.woff2` compression).*

### Command
```bash
python3 font.py
```
This regenerates the hinted TTFs in `fonts/ttf/` and the compressed `.woff2` files in `fonts/web/` using the same builder that produced the published releases.

## Changelog
- **2025-03-01:** Initial release of EasyType Sans, Focus, and Dyslexic families with Regular, Italic, Bold, and Bold Italic styles tuned specifically for neuro-divergent readers.

## Acknowledgements & credits
Designer: Andrzej Marczewski (<https://marczewski.me.uk>), inspired by cognitive psychology research on crowding, saccades, and reading fatigue.
The upstream builder draws from Google’s Noto sources, using fontTools automation to retain the original hint sets while applying EasyType’s anchoring, spacing, and rhythm adjustments.

## License
This Font Software is licensed under the SIL Open Font License, Version 1.1. The official notice lives in `OFL.txt` and is identical to the Google Fonts OFL template at <https://openfontlicense.org>.

## Packaging notes
When submitting, run `gftools packager "EasyType Sans"`, `gftools packager "EasyType Focus"`, and `gftools packager "EasyType Dyslexic"` from this repository root so that each family is pushed into its final `ofl/` directory with the matching `METADATA.pb` and article assets.

## Resources
* Website: <https://marczewski.me.uk/easytype>
* GitHub: <https://github.com/daverage/EasyType>
* Article: `documentation/article/ARTICLE.en_us.html`

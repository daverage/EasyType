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
Before running the packager you need a clone of the [`google/fonts`](https://github.com/google/fonts) repository (it must be a git repo with the `ofl/` hierarchy). From this builder root run:

```bash
gftools packager "EasyType Sans" /path/to/google/fonts
gftools packager "EasyType Focus" /path/to/google/fonts
gftools packager "EasyType Dyslexic" /path/to/google/fonts
```

The second argument is required because the packager copies each family into the separate `ofl/<family>` directory inside the Google Fonts repo; omitting it or pointing at this builder alone will raise `CRITICAL Repository not found at …`.

### Metadata helper
After building the fonts once, run the helper script to populate the newly created `METADATA.pb` files before rerunning the packager. For example:

```bash
python3 scripts/generate_packager_metadata.py /Users/andrzejmarczewski/Documents/GitHub/google-fonts --commit HEAD
```

The script writes the EasyType family metadata plus `OFL.txt` and the specimen article so `gftools packager` can copy everything into `google/fonts`. Re-run the same packager commands afterwards to finish the submission.

### Family-specific descriptions
Each family needs its own `DESCRIPTION.en_us.html`. Run `scripts/generate_family_descriptions.py` to emit a tailored description for `EasyType Sans`, `EasyType Focus`, and `EasyType Dyslexic` under `documentation/article-descriptions/<slug>/DESCRIPTION.en_us.html`. Copy the appropriate description (one per family) and `OFL.txt` into the `ofl/<family>` folder inside your `google/fonts` clone before running `gftools packager` so the submission has the right prose plus license file.

### Automated rebuild + packager run
When you want to regenerate everything and re-stage the families from scratch (cleaning old directories, rewriting metadata, and invoking `gftools packager` for each family), use:

```bash
export GH_TOKEN=your_token_here
scripts/rebuild_and_packager.sh /Users/andrzejmarczewski/Documents/GitHub/google-fonts HEAD
```

The script removes any existing `ofl/easytype…` folders in the Google Fonts clone, regenerates `METADATA.pb`, and runs the packager for each of the three families. `GH_TOKEN` must be set because `gftools packager` needs it to download the EasyType sources.

## Resources
* Website: <https://marczewski.me.uk/easytype>
* GitHub: <https://github.com/daverage/EasyType>
* Article: `documentation/article/ARTICLE.en_us.html`

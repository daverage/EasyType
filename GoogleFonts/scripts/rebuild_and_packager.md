# `rebuild_and_packager.sh`

This script automates the EasyType submission workflow inside this builder repository.  
It regenerates the `METADATA.pb` files, cleans each `google/fonts/ofl/<slug>` folder, and reruns `gftools packager` for every EasyType family in sequence.

## Usage

```bash
export GH_TOKEN=your_token
scripts/rebuild_and_packager.sh /path/to/google/fonts [commit]
```

| Argument | Description |
| --- | --- |
| `/path/to/google/fonts` | Path to the cloned `google/fonts` repository where the families should be staged. |
| `commit` | Optional; git ref that describes the source state (defaults to `HEAD`). This value ends up in each `METADATA.pb` `source.commit` field. |

## Behavior

1. Regenerates metadata for EasyType Sans, Focus, and Dyslexic via `scripts/generate_packager_metadata.py`.
2. For each family, removes its corresponding `ofl/<slug>` folder in the Google Fonts clone before invoking `gftools packager`, ensuring the latest assets land in a clean directory.
3. Requires `GH_TOKEN`, because `gftools packager` downloads the upstream EasyType sources.

## Requirements

- Build the fonts first with `python3 font.py` so `fonts/ttf/*.ttf` exist for packaging.
- Copy the family-specific `DESCRIPTION.en_us.html` plus `OFL.txt` into each `/path/to/google/fonts/ofl/<slug>` before the script runs so the packager can include them.

Run it whenever you want to refresh every EasyType family in `google/fonts` from scratch.

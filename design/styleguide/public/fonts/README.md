# Local fonts

OSS font files (`.woff2`) ship here and are loaded via `src/fonts.css` — **no
runtime web-font fetch** (hard constraint, context §8).

**Phase 1 wired the Instrument typefaces** (both SIL OFL 1.1, latin subset):

- `plex-sans-{400,500,600,700}.woff2` — IBM Plex Sans (UI / body), `--font-sans`
- `plex-mono-{400,500}.woff2` — IBM Plex Mono (data / traces / numbers), `--font-mono`

Source: the Fontsource distribution of IBM Plex. To refresh, re-download the
matching `latin-<weight>-normal.woff2` files. A display face may be added in
Phase 2B (the display role currently falls back to Plex Sans).

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Single-script Python project that generates a branded QR code. The script extracts
the dominant brand color from `logo.png`, renders a QR code in that color with rounded
modules, embeds the logo (on a white backing) in the center, and writes `qr_faros.png`.

## Commands

The project uses a local virtual environment (`.venv`, Python 3.14) and has no
`requirements.txt`. Install dependencies into the venv if missing:

```powershell
.venv\Scripts\python.exe -m pip install "qrcode[pil]" Pillow
```

Run the generator (regenerates `qr_faros.png` in place):

```powershell
.venv\Scripts\python.exe generate_qr.py
```

There are no tests, linters, or build steps.

## Architecture

`generate_qr.py` is the entire program. Configuration lives in module-level constants
at the top (`URL`, `LOGO_PATH`, `OUT_PATH`, `ERROR_CORRECTION`, `LOGO_RATIO`) — change
the target URL or logo there rather than via CLI args.

The pipeline in `main()` is four sequential steps, each a pure-ish helper:

- `extract_dominant_colors()` — quantizes the logo to a 16-color palette, drops
  near-white colors (`is_near_white`), and returns the darkest prominent colors.
  Element `[0]` (darkest) becomes the QR module fill color.
- `build_qr()` — builds the QR with `qrcode`'s `StyledPilImage` + `RoundedModuleDrawer`
  and a `SolidFillColorMask`.
- `embed_logo()` — scales the logo to `LOGO_RATIO` of the shorter side and pastes it
  centered with a white padded backing.

Two interdependencies to keep in mind when editing:

- The background is kept white (not the second extracted color) so the code stays
  scannable. Don't swap `back` to a colored value without checking contrast.
- `ERROR_CORRECT_H` (30% recovery) is what allows the centered logo to cover part of
  the code. If you increase `LOGO_RATIO`, the logo may exceed the recoverable area and
  break scannability.

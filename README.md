# Branded QR Code Generator

A single-file Python script that generates a branded QR code from any logo. It
extracts the logo's dominant brand colour, renders the QR with rounded modules
in that colour, and embeds the logo in the centre on a clean white backing.

![Example output](qr_faros.png)

## Features

- **Brand colour from the logo** — quantises the logo and picks its boldest
  (darkest, non-white) colour for the QR modules.
- **Works with any logo** — a transparent PNG, a logo on a white background, or
  a "badge" on a solid colour all work. A uniform background is detected and
  removed automatically, so it never hijacks the brand colour or shows as an
  edge around the logo.
- **Clean centred logo** — the logo is placed on a circular white backing sized
  to the logo itself, with no stray halo, square corners, or faint rings.
- **Scannable by design** — uses HIGH (30%) error correction so the centred
  logo can cover part of the code without breaking scanning.

## Requirements

- Python 3.10+
- [`qrcode[pil]`](https://pypi.org/project/qrcode/) and
  [`Pillow`](https://pypi.org/project/pillow/)

Install into a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install "qrcode[pil]" Pillow
```

## Usage

1. Put your logo next to the script as `logo.png`.
2. Edit the configuration block at the top of `generate_qr.py` (at minimum the
   `URL`).
3. Run it:

```powershell
.venv\Scripts\python.exe generate_qr.py
```

This writes the branded QR code to `qr_faros.png`.

## Configuration

All settings live in the configuration block at the top of `generate_qr.py`:

| Constant          | Purpose                                                                 |
| ----------------- | ----------------------------------------------------------------------- |
| `URL`             | The URL (or text) the QR code encodes.                                   |
| `LOGO_PATH`       | Path to the logo image (default: `logo.png`).                            |
| `OUT_PATH`        | Where the generated QR code is written (default: `qr_faros.png`).        |
| `ERROR_CORRECTION`| QR error-correction level (default: `ERROR_CORRECT_H`, 30%).             |
| `LOGO_RATIO`      | Fraction of the QR's shorter side the logo occupies (default: `0.28`).   |
| `AUTO_REMOVE_BG`  | Auto-detect and strip a uniform logo background (default: `True`).       |
| `BG_TOLERANCE`    | How close a colour must be to the corner colour to count as background.  |

> **Note:** increasing `LOGO_RATIO` too far can push the logo past the
> recoverable area and break scannability. Keep the logo around 25–30% of the
> code.

## How it works

`main()` runs four steps, each a small helper:

1. **`load_logo()`** — opens the logo and, when `AUTO_REMOVE_BG` is on, removes
   a uniform background (flood-fill from the corners), erodes the anti-aliased
   rim, and snaps near-white areas to pure white. This cleaned logo is the
   single source of truth used by the next steps.
2. **`extract_dominant_colors()`** — flattens the cleaned logo onto white and
   returns its boldest non-white colours, darkest first. Element `[0]` becomes
   the QR module colour.
3. **`build_qr()`** — builds the QR with `qrcode`'s `StyledPilImage`,
   `RoundedModuleDrawer`, and a `SolidFillColorMask`.
4. **`embed_logo()`** — places the cleaned logo, centred, on a white circular
   backing sized to the logo.

The background is always kept white so the code stays scannable.

## License

[MIT](LICENSE) © 2026 Vladimir Vukojičić

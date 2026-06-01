"""
Generates a branded QR code using colors extracted from logo.png.
Embeds the logo in the center of the QR code.

Requirements:
    pip install qrcode[pil] Pillow
"""

import sys
from pathlib import Path
from collections import Counter

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image

# ── Configuration ─────────────────────────────────────────────────────────────
URL       = "https://gooliverani.github.io/_farosplus/?"
LOGO_PATH = Path(__file__).parent / "logo.png"
OUT_PATH  = Path(__file__).parent / "qr_faros.png"

# QR error correction – HIGH (30 %) so the logo can cover part of the code
ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_H

# Logo will occupy this fraction of the QR code's shorter side
LOGO_RATIO = 0.28
# ──────────────────────────────────────────────────────────────────────────────


def is_near_white(rgb: tuple[int, int, int], threshold: int = 230) -> bool:
    """Return True if the colour is close to white / very light."""
    return all(c >= threshold for c in rgb)


def extract_dominant_colors(
    image_path: Path, n: int = 2, palette_size: int = 16
) -> list[tuple[int, int, int]]:
    """
    Quantise the image to *palette_size* colours and return the *n* most
    frequent non-white ones, darkest first.
    """
    # Composite onto white first: a logo with transparent areas would otherwise
    # expose black (alpha is dropped by convert("RGB")) and hijack the "darkest
    # colour" pick. Flattening to white keeps the brand colour as the boldest.
    src = Image.open(image_path).convert("RGBA")
    white = Image.new("RGBA", src.size, (255, 255, 255, 255))
    img = Image.alpha_composite(white, src).convert("RGB")
    # Quantise to a small palette for speed & robustness
    quantised = img.quantize(colors=palette_size).convert("RGB")

    width, height = quantised.size
    pixels = [quantised.getpixel((x, y)) for x in range(width) for y in range(height)]

    counts: Counter = Counter(pixels)
    candidates = [
        color for color, _ in counts.most_common()
        if not is_near_white(color)
    ]

    # Sort darkest → lightest so element [0] is the boldest colour
    candidates.sort(key=lambda c: sum(c))

    return candidates[:n]


def build_qr(
    url: str,
    fill_color: tuple[int, int, int],
    back_color: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Generate a QR code image with rounded modules."""
    qr = qrcode.QRCode(
        version=None,          # auto-size
        error_correction=ERROR_CORRECTION,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(
            front_color=fill_color,
            back_color=back_color,
        ),
    ).convert("RGB")

    return img


def embed_logo(qr_img: Image.Image, logo_path: Path, logo_ratio: float) -> Image.Image:
    """Paste the logo, centred, into the QR code image."""
    qr_img = qr_img.convert("RGBA")
    logo   = Image.open(logo_path).convert("RGBA")

    max_side  = int(min(qr_img.size) * logo_ratio)
    logo_w, logo_h = logo.size
    scale     = min(max_side / logo_w, max_side / logo_h)
    new_size  = (int(logo_w * scale), int(logo_h * scale))
    logo      = logo.resize(new_size, Image.LANCZOS)

    # White padded backing so the logo has a clean border
    pad       = int(max_side * 0.06)
    backing   = Image.new("RGBA",
                          (logo.width + pad * 2, logo.height + pad * 2),
                          (255, 255, 255, 255))
    backing.paste(logo, (pad, pad), logo)

    offset_x  = (qr_img.width  - backing.width)  // 2
    offset_y  = (qr_img.height - backing.height) // 2
    qr_img.paste(backing, (offset_x, offset_y), backing)

    return qr_img.convert("RGB")


def main() -> None:
    # Windows consoles default to cp1252, which can't encode non-ASCII output
    # (e.g. the arrow below). Force UTF-8 so the script never crashes on print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"Extracting colours from  : {LOGO_PATH}")
    colours = extract_dominant_colors(LOGO_PATH, n=2)
    fill    = colours[0]          # darkest prominent colour (navy blue)
    back    = (255, 255, 255)     # white background keeps QR scannable
    print(f"  Module colour (fill)   : #{fill[0]:02X}{fill[1]:02X}{fill[2]:02X}  {fill}")
    print(f"  Background colour      : #{back[0]:02X}{back[1]:02X}{back[2]:02X}  {back}")

    print(f"\nGenerating QR code for   : {URL}")
    qr_img = build_qr(URL, fill_color=fill, back_color=back)

    print(f"Embedding logo           : {LOGO_PATH.name}")
    final  = embed_logo(qr_img, LOGO_PATH, LOGO_RATIO)

    final.save(OUT_PATH, quality=95)
    print(f"\nSaved -> {OUT_PATH}")


if __name__ == "__main__":
    main()

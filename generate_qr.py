"""
Generates a branded QR code using colours extracted from a logo image.
Embeds the logo in the centre of the QR code on a clean white backing.

Works with any logo: transparent PNGs, logos on a white background, or a
"badge" logo that sits on a solid colour (e.g. a circle on black). A uniform
background is detected and removed automatically so it neither shows as an
edge around the logo nor hijacks the extracted brand colour.

Requirements:
    pip install qrcode[pil] Pillow

Usage:
    Point LOGO_PATH (and URL / OUT_PATH) at your files below and run:
        python generate_qr.py
"""

import sys
from pathlib import Path
from collections import Counter

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw, ImageChops, ImageFilter

# ── Configuration ─────────────────────────────────────────────────────────────
URL       = "https://gooliverani.github.io/_farosplus/?"
LOGO_PATH = Path(__file__).parent / "logo.png"
OUT_PATH  = Path(__file__).parent / "qr_faros.png"

# QR error correction – HIGH (30 %) so the logo can cover part of the code
ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_H

# Logo will occupy this fraction of the QR code's shorter side
LOGO_RATIO = 0.28

# Auto-remove a uniform background colour from the logo (set False to keep the
# logo exactly as supplied — e.g. if it is already transparent and you don't
# want any keying). BG_TOLERANCE is how close a colour must be to the sampled
# corner colour to count as background (0–441; higher removes more).
AUTO_REMOVE_BG = True
BG_TOLERANCE   = 60
# ──────────────────────────────────────────────────────────────────────────────


def is_near_white(rgb: tuple[int, int, int], threshold: int = 230) -> bool:
    """Return True if the colour is close to white / very light."""
    return all(c >= threshold for c in rgb)


def load_logo(image_path: Path) -> Image.Image:
    """
    Open the logo as RGBA and, if AUTO_REMOVE_BG is on, strip a uniform
    background so only the logo's marks remain (everything else transparent).
    This is the single source of truth used for both colour extraction and
    embedding, so the two always agree.
    """
    logo = Image.open(image_path).convert("RGBA")
    if AUTO_REMOVE_BG:
        logo = _remove_uniform_background(logo, tolerance=BG_TOLERANCE)
        logo = _flatten_near_white(logo)
    return logo


def _flatten_near_white(logo: Image.Image, threshold: int = 238) -> Image.Image:
    """
    Snap near-white pixels to pure #FFFFFF so an off-white logo field (or a
    soft vignette/halo) merges seamlessly with the white backing and the white
    QR background, leaving no faint ring. Only the logo's actual marks, which
    are well below the threshold, are kept.
    """
    r, g, b, a = logo.split()
    brightest_floor = ImageChops.darker(ImageChops.darker(r, g), b)
    near_white = brightest_floor.point(lambda v: 255 if v >= threshold else 0)
    pure = Image.new("RGB", logo.size, (255, 255, 255))
    rgb = Image.composite(pure, logo.convert("RGB"), near_white)
    rgb = rgb.convert("RGBA")
    rgb.putalpha(a)
    return rgb


def _remove_uniform_background(logo: Image.Image, tolerance: int) -> Image.Image:
    """
    Detect a uniform background by sampling the four corners and, if they
    agree, flood-fill it away from each corner. A short erosion of the
    resulting alpha removes the anti-aliased rim so no faint ring is left
    where the background met the logo.
    """
    w, h = logo.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    samples = [logo.getpixel(c) for c in corners]

    # Need mostly-opaque, mutually-agreeing corners to treat it as a solid bg.
    opaque = [s for s in samples if s[3] > 250]
    if len(opaque) < 3:
        return logo  # transparent or non-uniform corners → leave untouched
    bg = tuple(sum(s[i] for s in opaque) // len(opaque) for i in range(3))
    if max(_colour_distance(s[:3], bg) for s in opaque) > tolerance:
        return logo  # corners disagree → not a uniform background

    # Flood-fill the background region(s) with a sentinel colour, then key it
    # out. Flooding from the corners only removes background connected to the
    # edge, so same-coloured pixels *inside* the logo are preserved.
    sentinel = (1, 254, 1)
    flood = logo.convert("RGB")
    for c in corners:
        ImageDraw.floodfill(flood, c, sentinel, thresh=tolerance)
    fr, fg, fb = flood.split()
    bg_mask = ImageChops.multiply(
        ImageChops.multiply(fr.point(lambda v: 255 if v == 1 else 0),
                            fg.point(lambda v: 255 if v == 254 else 0)),
        fb.point(lambda v: 255 if v == 1 else 0),
    )

    alpha = ImageChops.subtract(logo.getchannel("A"), bg_mask)
    erode = max(1, round(min(w, h) * 0.004))
    alpha = alpha.filter(ImageFilter.MinFilter(erode * 2 + 1))
    logo.putalpha(alpha)
    return logo


def _colour_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def extract_dominant_colors(
    logo: Image.Image, n: int = 2, palette_size: int = 16
) -> list[tuple[int, int, int]]:
    """
    Quantise the logo to *palette_size* colours and return the *n* most
    frequent non-white ones, darkest first. The logo is flattened onto white
    so transparent/background areas read as white and get dropped, leaving the
    brand colour as the boldest pick (element [0]).
    """
    white = Image.new("RGBA", logo.size, (255, 255, 255, 255))
    img = Image.alpha_composite(white, logo).convert("RGB")
    quantised = img.quantize(colors=palette_size).convert("RGB")

    # getcolors returns (count, colour) pairs straight from the quantised image.
    counts = quantised.getcolors(maxcolors=palette_size * 2) or []
    candidates = [
        color for _, color in sorted(counts, reverse=True)
        if not is_near_white(color)
    ]
    candidates.sort(key=lambda c: sum(c))  # darkest → lightest
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


def embed_logo(qr_img: Image.Image, logo: Image.Image, logo_ratio: float) -> Image.Image:
    """Paste the (background-stripped) logo, centred, onto a white disc."""
    qr_img = qr_img.convert("RGBA")

    max_side  = int(min(qr_img.size) * logo_ratio)
    scale     = min(max_side / logo.width, max_side / logo.height)
    logo      = logo.resize((int(logo.width * scale), int(logo.height * scale)),
                            Image.LANCZOS)

    # Circular white backing sized to the logo itself (no extra halo): the
    # disc edge coincides with the logo's own circular edge, so the logo's
    # navy border ring sits right at the boundary with the QR modules.
    pad       = 0
    diameter  = max(logo.width, logo.height) + pad * 2

    ss        = 4
    disc_mask = Image.new("L", (diameter * ss, diameter * ss), 0)
    ImageDraw.Draw(disc_mask).ellipse(
        (0, 0, diameter * ss - 1, diameter * ss - 1), fill=255)
    disc_mask = disc_mask.resize((diameter, diameter), Image.LANCZOS)

    backing   = Image.composite(
        Image.new("RGBA", (diameter, diameter), (255, 255, 255, 255)),
        Image.new("RGBA", (diameter, diameter), (255, 255, 255, 0)),
        disc_mask,
    )

    lx = (diameter - logo.width)  // 2
    ly = (diameter - logo.height) // 2
    backing.paste(logo, (lx, ly), logo)

    offset_x = (qr_img.width  - diameter) // 2
    offset_y = (qr_img.height - diameter) // 2
    qr_img.paste(backing, (offset_x, offset_y), backing)

    return qr_img.convert("RGB")


def main() -> None:
    # Windows consoles default to cp1252, which can't encode non-ASCII output
    # (e.g. the arrow below). Force UTF-8 so the script never crashes on print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"Loading logo             : {LOGO_PATH}")
    logo = load_logo(LOGO_PATH)

    colours = extract_dominant_colors(logo, n=2)
    fill    = colours[0]          # darkest prominent colour (brand colour)
    back    = (255, 255, 255)     # white background keeps QR scannable
    print(f"  Module colour (fill)   : #{fill[0]:02X}{fill[1]:02X}{fill[2]:02X}  {fill}")
    print(f"  Background colour      : #{back[0]:02X}{back[1]:02X}{back[2]:02X}  {back}")

    print(f"\nGenerating QR code for   : {URL}")
    qr_img = build_qr(URL, fill_color=fill, back_color=back)

    print(f"Embedding logo           : {LOGO_PATH.name}")
    final  = embed_logo(qr_img, logo, LOGO_RATIO)

    final.save(OUT_PATH, quality=95)
    print(f"\nSaved -> {OUT_PATH}")


if __name__ == "__main__":
    main()

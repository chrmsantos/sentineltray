"""Generate assets/icon.ico — modern dark-badge eye icon for Z7_SentinelTray.

Run from the repository root:
    python scripts/generate_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


# ── Palette ───────────────────────────────────────────────────────────────────
_BG_DARK   = (11, 17, 27, 255)      # deep navy background
_BG_MID    = (17, 26, 42, 255)      # slightly lighter for top-light sheen
_SCLERA    = (228, 240, 235, 255)   # cool off-white
_LIMBUS    = (6, 32, 16, 255)       # dark outer iris ring
_IRIS_STEPS = [                     # outer → inner iris gradient
    (8,  42, 22),
    (13, 62, 32),
    (20, 88, 46),
    (30, 118, 60),
    (42, 150, 76),
    (55, 178, 92),
    (62, 196, 102),                 # peak brightness
    (52, 172, 87),
    (40, 145, 72),
    (28, 112, 56),
]
_PUPIL     = (4, 7, 5, 255)         # near-black pupil
_GLOW      = (0, 210, 90)           # iris glow colour
_BORDER    = (40, 200, 88, 210)     # eyelid outline
_WHITE     = (255, 255, 255)


def _make_icon(size: int) -> Image.Image:
    """Render a modern dark-badge eye icon at *size* × *size* pixels."""
    scale = 4
    s = size * scale
    cx, cy = s // 2, s // 2

    # ── 1. Background: dark rounded square ───────────────────────────────────
    base = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(base)
    corner_r = int(s * 0.22)
    bd.rounded_rectangle([0, 0, s - 1, s - 1], radius=corner_r, fill=_BG_DARK)

    # Subtle top-lit sheen: semi-transparent lighter ellipse near top
    sheen = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sw, sh_ = int(s * 0.70), int(s * 0.35)
    sd.ellipse(
        [cx - sw // 2, -sh_ // 2, cx + sw // 2, sh_ // 2 + int(s * 0.08)],
        fill=(255, 255, 255, 14),
    )
    base = Image.alpha_composite(base, sheen)

    # ── 2. Soft iris glow behind the eye ─────────────────────────────────────
    iris_r = int(s * 0.205)
    glow_layers = 10
    glow_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for i in range(glow_layers):
        spread = int(s * 0.018) * (glow_layers - i)
        alpha = 6 + i * 2
        gr = iris_r + spread
        gd.ellipse(
            [cx - gr, cy - gr, cx + gr, cy + gr],
            fill=(*_GLOW, alpha),
        )
    # Blur the glow for a smooth halo
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(s * 0.04)))
    base = Image.alpha_composite(base, glow_layer)

    # ── 3. Eye content ────────────────────────────────────────────────────────
    ew = int(s * 0.80)
    eh = int(s * 0.46)
    ex0, ey0 = cx - ew // 2, cy - eh // 2
    ex1, ey1 = ex0 + ew, ey0 + eh

    eye_content = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ec = ImageDraw.Draw(eye_content)

    # Sclera
    ec.ellipse([ex0, ey0, ex1, ey1], fill=_SCLERA)

    # Iris gradient (multiple concentric filled circles, outer → inner)
    steps = len(_IRIS_STEPS)
    for i, colour in enumerate(_IRIS_STEPS):
        frac = (steps - i) / steps
        r = int(iris_r * frac)
        ec.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*colour, 255))

    # Pupil
    pupil_r = int(s * 0.100)
    ec.ellipse(
        [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
        fill=_PUPIL,
    )

    # Primary catchlight — upper-right, bright
    hl1_r = max(2, int(s * 0.040))
    hl1_x = cx + int(s * 0.072)
    hl1_y = cy - int(s * 0.072)
    ec.ellipse(
        [hl1_x - hl1_r, hl1_y - hl1_r, hl1_x + hl1_r, hl1_y + hl1_r],
        fill=(*_WHITE, 230),
    )

    # Secondary catchlight — lower-left, dim
    hl2_r = max(1, int(s * 0.018))
    hl2_x = cx - int(s * 0.082)
    hl2_y = cy + int(s * 0.056)
    ec.ellipse(
        [hl2_x - hl2_r, hl2_y - hl2_r, hl2_x + hl2_r, hl2_y + hl2_r],
        fill=(*_WHITE, 100),
    )

    # ── 4. Mask eye content to almond shape ──────────────────────────────────
    eye_mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(eye_mask).ellipse([ex0, ey0, ex1, ey1], fill=255)

    eye_masked = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    eye_masked.paste(eye_content, mask=eye_mask)

    # ── 5. Eyelid border ─────────────────────────────────────────────────────
    border_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    border_w = max(2, int(s * 0.022))
    ImageDraw.Draw(border_layer).ellipse(
        [ex0, ey0, ex1, ey1],
        outline=_BORDER,
        width=border_w,
    )

    # ── 6. Composite ─────────────────────────────────────────────────────────
    result = Image.alpha_composite(base, eye_masked)
    result = Image.alpha_composite(result, border_layer)

    return result.resize((size, size), Image.LANCZOS)


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]

    assets_dir = Path(__file__).resolve().parents[1] / "assets"
    assets_dir.mkdir(exist_ok=True)

    ico_path = assets_dir / "icon.ico"
    png_path = assets_dir / "icon_256.png"

    frames = [_make_icon(sz) for sz in sizes]

    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(sz, sz) for sz in sizes],
        append_images=frames[1:],
    )
    print(f"[OK] {ico_path}")

    frames[-1].save(png_path, format="PNG")
    print(f"[OK] {png_path}")


if __name__ == "__main__":
    main()

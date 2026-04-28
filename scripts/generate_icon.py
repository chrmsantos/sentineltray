"""Generate assets/icon.ico -- green eye icon for Z7_SentinelTray.

Run from the repository root:
    python scripts/generate_icon.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


# -- Palette ------------------------------------------------------------------
_BG_DARK = (11, 17, 27, 255)   # deep navy background



def _make_icon(size: int) -> Image.Image:
    """Render a green eye icon on a dark rounded background at *size* x *size*."""
    scale = 4
    s = size * scale
    cx, cy = s // 2, s // 2

    # 1. Background: dark rounded square + subtle top sheen
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    corner_r = int(s * 0.22)
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=corner_r, fill=_BG_DARK
    )
    sheen = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sw_sh, sh_sh = int(s * 0.70), int(s * 0.32)
    ImageDraw.Draw(sheen).ellipse(
        [cx - sw_sh // 2, -sh_sh // 2, cx + sw_sh // 2, sh_sh // 2 + int(s * 0.06)],
        fill=(255, 255, 255, 12),
    )
    img = Image.alpha_composite(img, sheen)

    # 2. Soft green glow behind the eye
    glow_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    for i in range(10):
        gr = int(s * (0.26 + i * 0.025))
        alpha = 6 + i * 3
        ImageDraw.Draw(glow_layer).ellipse(
            [cx - gr, cy - gr, cx + gr, cy + gr],
            fill=(63, 185, 80, alpha),
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(s * 0.06)))
    img = Image.alpha_composite(img, glow_layer)

    # 3. Eye shape
    ew = int(s * 0.78)
    eh = int(s * 0.48)
    ex0, ey0 = cx - ew // 2, cy - eh // 2
    ex1, ey1 = ex0 + ew, ey0 + eh

    eye_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eye_layer)

    # Sclera (eye-white)
    ed.ellipse([ex0, ey0, ex1, ey1], fill=(255, 255, 255, 255))

    # Outer iris — deep forest green
    iris_r = int(s * 0.20)
    ed.ellipse(
        [cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r],
        fill=(27, 94, 32, 255),
    )
    # Mid iris — vibrant green
    mid_r = int(s * 0.155)
    ed.ellipse(
        [cx - mid_r, cy - mid_r, cx + mid_r, cy + mid_r],
        fill=(46, 204, 113, 255),
    )
    # Inner iris ring
    inner_r = int(s * 0.115)
    ed.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=(39, 174, 96, 255),
    )
    # Pupil
    pupil_r = int(s * 0.075)
    ed.ellipse(
        [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
        fill=(10, 10, 10, 255),
    )
    # Catchlight highlight
    hl_r = max(3, int(s * 0.036))
    hl_x = cx + int(s * 0.065)
    hl_y = cy - int(s * 0.065)
    ed.ellipse(
        [hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r],
        fill=(255, 255, 255, 255),
    )

    # Clip eye contents to the lens shape
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([ex0, ey0, ex1, ey1], fill=255)
    clipped = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    clipped.paste(eye_layer, mask=mask)

    # Eyelid border
    border_w = max(2, int(s * 0.022))
    ImageDraw.Draw(clipped).ellipse(
        [ex0, ey0, ex1, ey1], outline=(13, 77, 13, 255), width=border_w
    )

    # Upper eyelash accent lines
    lash_color = (13, 77, 13, 200)
    lash_len = int(s * 0.065)
    lash_w = max(2, int(s * 0.016))
    ld = ImageDraw.Draw(clipped)
    for i in range(5):
        angle_rad = math.radians(210 + i * 30)
        sx = int(cx + (ew // 2) * math.cos(angle_rad))
        sy = int(cy + (eh // 2) * math.sin(angle_rad))
        ex_end = int(sx + lash_len * math.cos(angle_rad))
        ey_end = int(sy + lash_len * math.sin(angle_rad))
        ld.line([sx, sy, ex_end, ey_end], fill=lash_color, width=lash_w)

    img = Image.alpha_composite(img, clipped)

    return img.resize((size, size), Image.LANCZOS)


def main():
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
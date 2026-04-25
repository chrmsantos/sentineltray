"""Generate assets/icon.ico — green eye icon for Z7_SentinelTray.

Run from the repository root:
    python scripts/generate_icon.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


def _make_eye(size: int) -> Image.Image:
    """Draw a green eye icon at *size* x *size* pixels using 4x supersampling."""
    scale = 4
    s = size * scale
    cx, cy = s // 2, s // 2

    # Eye-shape bounding box (horizontal lens / almond)
    ew = int(s * 0.88)
    eh = int(s * 0.52)
    ex0, ey0 = cx - ew // 2, cy - eh // 2
    ex1, ey1 = ex0 + ew, ey0 + eh

    # ── content layer (everything before masking) ────────────────────
    content = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cd = ImageDraw.Draw(content)

    # Sclera (eye-white), fills the whole canvas — mask will clip it
    cd.ellipse([ex0, ey0, ex1, ey1], fill=(255, 255, 255, 255))

    # Outer iris ring — deep forest green
    iris_r = int(s * 0.21)
    cd.ellipse(
        [cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r],
        fill=(27, 94, 32, 255),
    )

    # Mid iris — vibrant green
    mid_r = int(s * 0.17)
    cd.ellipse(
        [cx - mid_r, cy - mid_r, cx + mid_r, cy + mid_r],
        fill=(46, 204, 113, 255),
    )

    # Inner iris ring — slightly lighter for depth
    inner_r = int(s * 0.13)
    cd.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=(39, 174, 96, 255),
    )

    # Pupil
    pupil_r = int(s * 0.085)
    cd.ellipse(
        [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
        fill=(10, 10, 10, 255),
    )

    # Catchlight (white highlight)
    hl_r = max(3, int(s * 0.038))
    hl_x = cx + int(s * 0.07)
    hl_y = cy - int(s * 0.07)
    cd.ellipse(
        [hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r],
        fill=(255, 255, 255, 255),
    )

    # ── alpha mask — only the eye-lens shape is visible ──────────────
    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([ex0, ey0, ex1, ey1], fill=255)

    # Composite: content visible only inside lens mask
    result = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    result.paste(content, mask=mask)

    # Eyelid border drawn on top of composited image
    border = ImageDraw.Draw(result)
    border_w = max(2, int(s * 0.025))
    border.ellipse(
        [ex0, ey0, ex1, ey1],
        outline=(13, 77, 13, 255),
        width=border_w,
    )

    # Eyelash accent lines (upper lid, 5 lashes)
    lash_color = (13, 77, 13, 200)
    lash_len = int(s * 0.07)
    lash_w = max(2, int(s * 0.018))
    num_lashes = 5
    for i in range(num_lashes):
        angle_deg = 180 + 30 + i * (120 // (num_lashes - 1))  # 210..330°
        angle_rad = math.radians(angle_deg)
        # Start point: on the upper eyelid ellipse edge
        sx = int(cx + (ew // 2) * math.cos(angle_rad))
        sy = int(cy + (eh // 2) * math.sin(angle_rad))
        # End point: slightly outward
        ex = int(sx + lash_len * math.cos(angle_rad))
        ey_end = int(sy + lash_len * math.sin(angle_rad))
        border.line([sx, sy, ex, ey_end], fill=lash_color, width=lash_w)

    # Downsample with high-quality LANCZOS filter for smooth antialiasing
    return result.resize((size, size), Image.LANCZOS)


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]

    assets_dir = Path(__file__).resolve().parents[1] / "assets"
    assets_dir.mkdir(exist_ok=True)

    ico_path = assets_dir / "icon.ico"
    png_path = assets_dir / "icon_256.png"

    frames = [_make_eye(sz) for sz in sizes]

    # Save multi-size .ico
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(sz, sz) for sz in sizes],
        append_images=frames[1:],
    )
    print(f"[OK] {ico_path}")

    # Save 256px PNG (for preview / README)
    frames[-1].save(png_path, format="PNG")
    print(f"[OK] {png_path}")


if __name__ == "__main__":
    main()

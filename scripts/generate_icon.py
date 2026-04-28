"""Generate assets/icon.ico -- sentinel watchtower icon for Z7_SentinelTray.

Run from the repository root:
    python scripts/generate_icon.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


# -- Palette ------------------------------------------------------------------
_BG_DARK      = (11, 17, 27, 255)     # deep navy background
_TOWER_BODY   = (38, 52, 72, 255)     # tower main face
_TOWER_LIGHT  = (62, 82, 108, 255)    # tower lit (left) edge
_TOWER_SHADOW = (22, 30, 44, 255)     # tower shadow (right) edge
_MERLON       = (48, 64, 88, 255)     # battlement merlon body
_MERLON_TOP   = (78, 100, 132, 255)   # merlon top-edge highlight
_STONE_LINE   = (18, 25, 37, 180)     # horizontal mortar lines
_GLOW         = (0, 210, 90)          # beacon / window glow (green accent)
_BEAM         = (0, 220, 100)         # searchlight beam tint
_ACCENT       = (40, 200, 88, 170)    # outline accent
_WINDOW_DARK  = (12, 20, 30, 255)     # window border / frame


def _draw_arch_window(
    draw,
    cx,
    cy,
    w,
    h,
    fill,
    outline=None,
    outline_w=2,
):
    """Draw a Gothic arched window: rectangular body + semicircle top."""
    arch_r = w // 2
    x0, x1 = cx - w // 2, cx + w // 2
    rect_top = cy - h // 2 + arch_r
    rect_bot = cy + h // 2
    draw.rectangle([x0, rect_top, x1, rect_bot], fill=fill)
    draw.ellipse([x0, cy - h // 2, x1, cy - h // 2 + arch_r * 2], fill=fill)
    if outline:
        draw.rectangle([x0, rect_top, x1, rect_bot], outline=outline, width=outline_w)
        draw.ellipse(
            [x0, cy - h // 2, x1, cy - h // 2 + arch_r * 2],
            outline=outline,
            width=outline_w,
        )


def _make_icon(size):
    """Render a sentinel watchtower icon at *size* x *size* pixels."""
    scale = 4
    s = size * scale
    cx, cy = s // 2, s // 2

    # 1. Background: dark rounded square + top sheen
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    corner_r = int(s * 0.22)
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=corner_r, fill=_BG_DARK
    )
    sheen = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sw, sh = int(s * 0.70), int(s * 0.32)
    ImageDraw.Draw(sheen).ellipse(
        [cx - sw // 2, -sh // 2, cx + sw // 2, sh // 2 + int(s * 0.06)],
        fill=(255, 255, 255, 12),
    )
    img = Image.alpha_composite(img, sheen)

    # 2. Searchlight beam (behind tower)
    battle_base_y = int(s * 0.290)
    m_h = int(s * 0.090)
    beam_origin_y = battle_base_y - m_h // 2

    center_angle = math.radians(42)
    beam_length = int(s * 0.62)
    beam_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    for i in range(10):
        half_spread = math.radians(16 + i * 3)
        alpha = int(26 * (10 - i) / 10)
        pts = [
            (cx, beam_origin_y),
            (
                cx + int(beam_length * math.sin(center_angle - half_spread)),
                beam_origin_y - int(beam_length * math.cos(center_angle - half_spread)),
            ),
            (
                cx + int(beam_length * math.sin(center_angle + half_spread)),
                beam_origin_y - int(beam_length * math.cos(center_angle + half_spread)),
            ),
        ]
        ImageDraw.Draw(beam_layer).polygon(pts, fill=(*_BEAM, alpha))
    beam_layer = beam_layer.filter(ImageFilter.GaussianBlur(radius=int(s * 0.030)))
    img = Image.alpha_composite(img, beam_layer)

    # 3. Tower body (trapezoid, slightly narrower at top)
    tower_w = int(s * 0.50)
    tower_x0 = cx - tower_w // 2
    tower_x1 = cx + tower_w // 2
    tower_base_y = int(s * 0.880)
    taper = int(s * 0.022)
    top_x0 = tower_x0 + taper
    top_x1 = tower_x1 - taper

    body_pts = [
        (top_x0, battle_base_y),
        (top_x1, battle_base_y),
        (tower_x1, tower_base_y),
        (tower_x0, tower_base_y),
    ]
    tower_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    td = ImageDraw.Draw(tower_layer)
    td.polygon(body_pts, fill=_TOWER_BODY)

    # Left-side lit edge strip
    hl_w = int(tower_w * 0.13)
    td.polygon(
        [
            (top_x0, battle_base_y),
            (top_x0 + hl_w, battle_base_y),
            (tower_x0 + hl_w, tower_base_y),
            (tower_x0, tower_base_y),
        ],
        fill=_TOWER_LIGHT,
    )
    # Right-side shadow edge strip
    sh_w = int(tower_w * 0.10)
    td.polygon(
        [
            (top_x1 - sh_w, battle_base_y),
            (top_x1, battle_base_y),
            (tower_x1, tower_base_y),
            (tower_x1 - sh_w, tower_base_y),
        ],
        fill=_TOWER_SHADOW,
    )
    # Horizontal stone mortar lines
    for row in range(1, 9):
        frac = row / 9
        ry = int(battle_base_y + (tower_base_y - battle_base_y) * frac)
        rx0 = int(tower_x0 + taper * (1 - frac))
        rx1 = int(tower_x1 - taper * (1 - frac))
        td.line([(rx0, ry), (rx1, ry)], fill=_STONE_LINE, width=max(1, int(s * 0.004)))

    # 4. Battlements (3 merlons, 2 crenels)
    m_w = int(s * 0.092)
    gap_w = int(s * 0.058)
    parapet_h = int(s * 0.022)

    p_x0 = top_x0 - int(s * 0.020)
    p_x1 = top_x1 + int(s * 0.020)
    p_y0 = battle_base_y
    p_y1 = battle_base_y + parapet_h
    td.rectangle([p_x0, p_y0, p_x1, p_y1], fill=_TOWER_LIGHT)

    merlon_top_y = battle_base_y - m_h
    total_batt_w = 3 * m_w + 2 * gap_w
    batt_x0 = cx - total_batt_w // 2

    for i in range(3):
        mx0 = batt_x0 + i * (m_w + gap_w)
        mx1 = mx0 + m_w
        td.rectangle([mx0, merlon_top_y, mx1, p_y1], fill=_MERLON)
        hl = max(1, int(s * 0.008))
        td.rectangle([mx0, merlon_top_y, mx1, merlon_top_y + hl], fill=_MERLON_TOP)
        td.rectangle([mx0, merlon_top_y, mx0 + hl, p_y1], fill=_MERLON_TOP)

    img = Image.alpha_composite(img, tower_layer)

    # 5. Beacon window with green glow
    win_cx = cx
    win_cy = int(battle_base_y + (tower_base_y - battle_base_y) * 0.38)
    win_w = int(s * 0.136)
    win_h = int(s * 0.188)

    glow_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    for i in range(14):
        spread = int(s * 0.013) * (14 - i)
        alpha = 3 + i * 4
        gw = win_w // 2 + spread
        gh = win_h // 2 + spread
        ImageDraw.Draw(glow_layer).ellipse(
            [win_cx - gw, win_cy - gh, win_cx + gw, win_cy + gh],
            fill=(*_GLOW, alpha),
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(s * 0.040)))
    img = Image.alpha_composite(img, glow_layer)

    win_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    border_w = max(2, int(s * 0.015))
    _draw_arch_window(
        ImageDraw.Draw(win_layer),
        win_cx, win_cy, win_w, win_h,
        fill=(*_GLOW, 248),
        outline=_WINDOW_DARK,
        outline_w=border_w,
    )
    img = Image.alpha_composite(img, win_layer)

    # 6. Tower accent outline
    outline_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ow = max(2, int(s * 0.011))
    ImageDraw.Draw(outline_layer).polygon(body_pts, outline=_ACCENT, width=ow)
    img = Image.alpha_composite(img, outline_layer)

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
#!/usr/bin/env python3
"""Generate the animated GitHub profile banners for @riccardoponte.

Run from the repository root:
    python scripts/banner/generate.py
"""

from __future__ import annotations

from collections import deque
import html
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

try:
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
except ImportError:
    linear_sum_assignment = None
    cdist = None


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/source/avatar.png"
ASSETS = ROOT / "assets"
LOGOS = Path(__file__).resolve().parent / "logos"
DATA = Path(__file__).resolve().parent / "data"

W, H = 1180, 610
LOOP_SECONDS = 14.2
INTRO_SECONDS = 3.2
TRAVELLER_COUNT = 900
SEED = 314159

ROWS = [
    ("Subject", "Riccardo Giorgio Ponte"),
    ("Handle", "@riccardoponte"),
    ("Origin", "Milano, Italia"),
    ("Focus", "AI Agents · Full-Stack · Automation"),
    ("Status", "Building + Shipping Real Tools"),
    ("Core.Lang", "Python · TypeScript · JavaScript"),
    ("Core.Web", "HTML · CSS · React · PWA"),
    ("Core.Mobile", "Kotlin · Jetpack Compose · C#"),
    ("Core.AI", "Copilot SDK · Foundry · PyRIT · OCR"),
    ("ToolChain", "VS Code · Playwright · Chrome MV3 · Git"),
    ("Highlight", "Microsoft Hackathon · Chrome Web Store"),
    ("Grid.GitHub", "github.com/riccardoponte"),
    ("Grid.LinkedIn", "/in/riccardo-ponte"),
    ("Grid.Instagram", "@rickiponte"),
]

THEMES = {
    "dark": {
        "bg": "#070B14",
        "panel": "#0C1322",
        "panel2": "#10192D",
        "line": "#1E2D4A",
        "muted": "#7C90B0",
        "text": "#E2ECF8",
        "portrait": "#38BDF8",
        "chrome": "#2DD4BF",
        "accent": "#34D399",
        "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA",
        "panel": "#FFFFFF",
        "panel2": "#F0F5FA",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#0F172A",
        "portrait": "#0369A1",
        "chrome": "#0D9488",
        "accent": "#059669",
        "shadow": "#94A3B8",
    },
}


def make_logos() -> dict[str, Image.Image]:
    """Create clean 400px black-on-transparent silhouette sources."""
    LOGOS.mkdir(parents=True, exist_ok=True)
    size = 400
    logos: dict[str, Image.Image] = {}

    # 1. AI Neural / Agent spark with connected satellite nodes.
    ai = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(ai)
    star: list[tuple[float, float]] = []
    for i in range(16):
        a = -math.pi / 2 + i * math.pi / 8
        radius = 138 if i % 4 == 0 else (46 if i % 2 == 0 else 26)
        star.append((200 + math.cos(a) * radius, 200 + math.sin(a) * radius))
    d.polygon(star, fill="black")
    nodes = [(82, 108), (320, 108), (324, 298), (80, 304)]
    for a, b in zip(nodes, nodes[1:] + nodes[:1]):
        d.line([a, b], fill="black", width=12)
    for x, y in nodes:
        d.ellipse((x - 19, y - 19, x + 19, y + 19), fill="black")
    logos["ai"] = ai

    # 2. </> mark built from broad, rounded strokes.
    code = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(code)
    stroke = 42
    d.line([(154, 95), (66, 200), (154, 305)], fill="black", width=stroke, joint="curve")
    d.line([(246, 95), (334, 200), (246, 305)], fill="black", width=stroke, joint="curve")
    d.line([(225, 72), (174, 328)], fill="black", width=stroke)
    logos["code"] = code

    # 3. Hexagonal terminal prompt >_ mark.
    terminal = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(terminal)
    center = np.array([200.0, 200.0])
    outer_hex = [
        tuple(center + 168 * np.array([math.cos(-math.pi / 2 + i * math.tau / 6), math.sin(-math.pi / 2 + i * math.tau / 6)]))
        for i in range(6)
    ]
    inner_hex = [
        tuple(center + 128 * np.array([math.cos(-math.pi / 2 + i * math.tau / 6), math.sin(-math.pi / 2 + i * math.tau / 6)]))
        for i in range(6)
    ]
    d.polygon(outer_hex, fill="black")
    d.polygon(inner_hex, fill=(0, 0, 0, 0))
    d.line([(135, 152), (195, 200), (135, 248)], fill="black", width=28, joint="curve")
    d.line([(212, 246), (272, 246)], fill="black", width=28)
    logos["terminal"] = terminal

    for name, image in logos.items():
        image.save(LOGOS / f"{name}.png", optimize=True)
    return logos


def extract_subject_rgba(image: Image.Image) -> Image.Image:
    """Remove studio white backdrop and outer scan-edge corner triangles."""
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba).copy()
    h, w, _ = arr.shape

    # Clean tiny dark corner triangles from tilted studio scans before flood fill.
    arr[:18, :w] = [255, 255, 255, 255]
    arr[:, :18] = [255, 255, 255, 255]
    arr[:, w - 18 :] = [255, 255, 255, 255]

    rgb = arr[:, :, :3].astype(np.int16)
    brightness = rgb.mean(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    # Studio backdrop + subtle neck shadow on the wall have low chroma and high brightness;
    # warm skin has higher chroma and the dark shirt has low brightness.
    is_bg_candidate = (brightness >= 195) & (chroma <= 20)

    bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for sx, sy in [(0, 0), (w - 1, 0), (0, h // 2), (w - 1, h // 2), (w // 2, 0)]:
        if is_bg_candidate[sy, sx]:
            bg[sy, sx] = True
            q.append((sx, sy))

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny, nx] and is_bg_candidate[ny, nx]:
                bg[ny, nx] = True
                q.append((nx, ny))

    # Remove tiny isolated background speckles, keeping the main head+shoulders component.
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(radius=1.0))
    arr[:, :, 3] = np.asarray(alpha_img)
    return Image.fromarray(arr, "RGBA")


def floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    """Serpentine 1-bit Floyd-Steinberg diffusion; True means a lit pixel."""
    work = gray.astype(np.float32) / 255.0
    out = np.zeros_like(work, dtype=bool)
    height, width = work.shape
    for y in range(height):
        left_to_right = y % 2 == 0
        xs = range(width) if left_to_right else range(width - 1, -1, -1)
        direction = 1 if left_to_right else -1
        for x in xs:
            old = work[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            out[y, x] = bool(new)
            err = old - new
            nx = x + direction
            if 0 <= nx < width:
                work[y, nx] += err * 7 / 16
            if y + 1 < height:
                if 0 <= x - direction < width:
                    work[y + 1, x - direction] += err * 3 / 16
                work[y + 1, x] += err * 5 / 16
                if 0 <= nx < width:
                    work[y + 1, nx] += err * 1 / 16
    return out


def portrait_points(theme: str, rng: np.random.Generator) -> np.ndarray:
    """Return sampled x/y banner coordinates from a 300x340 dither grid."""
    source = extract_subject_rgba(Image.open(SOURCE))
    # Tighter head + shoulders framing (650x737 -> 300x340).
    crop = source.crop((75, 63, 725, 800)).resize((300, 340), Image.Resampling.LANCZOS)
    rgb = crop.convert("RGB")
    alpha = np.asarray(crop.getchannel("A"), dtype=np.float32) / 255.0

    if theme == "dark":
        lum = np.asarray(ImageOps.grayscale(rgb), dtype=np.float32)
        # Keep dark shirt contours faintly visible on dark backgrounds.
        edges = np.asarray(ImageOps.grayscale(rgb).filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        boosted = np.clip(np.maximum(lum, 26.0 + edges * 0.45) * alpha, 0, 255)
        prepared = Image.fromarray(np.uint8(boosted), "L")
        mask = Image.fromarray(np.uint8((alpha > 0.12) * 255), "L")
        prepared = ImageOps.equalize(prepared, mask=mask)
        select_lit = True
    else:
        white = Image.new("RGBA", crop.size, "white")
        white.alpha_composite(crop)
        prepared = ImageOps.grayscale(white.convert("RGB"))
        prepared = ImageOps.autocontrast(prepared, cutoff=1)
        select_lit = False

    prepared = ImageEnhance.Contrast(prepared).enhance(1.32)
    prepared = prepared.filter(ImageFilter.UnsharpMask(radius=2, percent=170, threshold=1))
    bits = floyd_steinberg(np.asarray(prepared))
    active = bits if select_lit else ~bits
    if theme == "dark":
        active &= alpha > 0.12

    ys, xs = np.where(active)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    points = np.column_stack((74 + xs, 154 + ys)).astype(np.float32)
    if len(points) > 18000:
        points = points[rng.choice(len(points), 18000, replace=False)]
    return points


def sample_logo_points(
    image: Image.Image, rng: np.random.Generator, count: int
) -> np.ndarray:
    """Sample a silhouette into the portrait frame's visual coordinate space."""
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > 127)
    chosen = rng.choice(len(xs), count, replace=len(xs) < count)
    return np.column_stack((89 + xs[chosen] * 0.675, 188 + ys[chosen] * 0.675)).astype(
        np.float32
    )


def _hungarian_numpy(cost: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pure-NumPy Jonker-Volgenant / Hungarian O(n^3) solver fallback."""
    n = cost.shape[0]
    u = np.zeros(n + 1, dtype=np.float64)
    v = np.zeros(n + 1, dtype=np.float64)
    p = np.zeros(n + 1, dtype=np.int32)
    way = np.zeros(n + 1, dtype=np.int32)
    inf = 1e18

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(n + 1, inf, dtype=np.float64)
        used = np.zeros(n + 1, dtype=bool)
        row_cost = cost[i - 1]
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            cur = cost[i0 - 1] - u[i0] - v[1:]
            mask = ~used[1:]
            unvisited = np.where(mask)[0] + 1
            diffs = cur[mask]
            improved = diffs < minv[unvisited]
            upd_idx = unvisited[improved]
            minv[upd_idx] = diffs[improved]
            way[upd_idx] = j0
            best_pos = int(np.argmin(minv[unvisited]))
            j1 = int(unvisited[best_pos])
            delta = float(minv[j1])
            visited = np.where(used)[0]
            u[p[visited]] += delta
            v[visited] -= delta
            minv[unvisited] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    row_ind = p[1:] - 1
    col_ind = np.arange(n, dtype=np.int32)
    order = np.argsort(row_ind)
    return row_ind[order], col_ind[order]


def transport(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Order target points by minimum-cost assignment from source points."""
    if linear_sum_assignment is not None and cdist is not None:
        dist = cdist(source, target, metric="sqeuclidean")
        rows, cols = linear_sum_assignment(dist)
    else:
        diff = source[:, None, :] - target[None, :, :]
        dist = np.einsum("ijk,ijk->ij", diff, diff).astype(np.float64)
        rows, cols = _hungarian_numpy(dist)
    ordered = np.empty_like(target)
    ordered[rows] = target[cols]
    return ordered


def num(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def point_path(points: np.ndarray) -> str:
    """Aggregate adjacent horizontal one-pixel dots into compact SVG path runs."""
    if not len(points):
        return ""
    integer = np.rint(points).astype(int)
    unique = sorted({(int(x), int(y)) for x, y in integer}, key=lambda p: (p[1], p[0]))
    chunks: list[str] = []
    i = 0
    while i < len(unique):
        x0, y = unique[i]
        x1 = x0
        i += 1
        while i < len(unique) and unique[i][1] == y and unique[i][0] <= x1 + 1:
            x1 = unique[i][0]
            i += 1
        chunks.append(f"M{x0} {y}h{x1 - x0 + 1}")
    return "".join(chunks)


def dotted_leader(x1: float, x2: float, y: float) -> str:
    if x2 <= x1:
        return ""
    return "".join(f"M{x} {num(y)}h1" for x in np.arange(x1, x2, 5.0))


def text_width(text: str, font_size: float) -> float:
    return len(text) * font_size * 0.605


def animate_values(points: list[np.ndarray], index: int) -> str:
    return ";".join(f"{num(p[index, 0])} {num(p[index, 1])}" for p in points)


def render_svg(
    theme_name: str,
    portrait: np.ndarray,
    logo_points: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> str:
    t = THEMES[theme_name]
    n = min(TRAVELLER_COUNT, len(portrait))
    source = portrait[rng.choice(len(portrait), n, replace=False)]
    ai = transport(source, logo_points["ai"][:n])
    code = transport(ai, logo_points["code"][:n])
    terminal = transport(code, logo_points["terminal"][:n])

    times = [0, 3.0, 4.3, 6.3, 7.6, 9.6, 10.9, 12.9, 14.2]
    key_times = ";".join(num(v / LOOP_SECONDS) for v in times)
    frames = [source, source, ai, ai, code, code, terminal, terminal, source]
    opacity_values = "0;0;1;1;1;1;1;1;0"

    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-labelledby="title desc">',
        '<title id="title">Riccardo Ponte live system profile</title>',
        '<desc id="desc">Animated terminal profile with a dithered portrait and '
        "AI, code, and terminal silhouettes.</desc>",
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{t["shadow"]}" '
        'flood-opacity=".28"/></filter>',
        '<filter id="glow" x="-100%" y="-100%" width="300%" height="300%">'
        f'<feGaussianBlur stdDeviation="3" result="b"/><feFlood flood-color="{t["chrome"]}" '
        'flood-opacity=".35"/><feComposite in2="b" operator="in"/>'
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<clipPath id="visualClip"><rect x="49" y="124" width="390" height="414" rx="3"/></clipPath>',
        "</defs>",
        f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>',
        f'<rect x="13" y="13" width="1154" height="584" rx="13" fill="{t["panel"]}" '
        f'stroke="{t["line"]}" filter="url(#shadow)"/>',
        f'<path d="M13 62H1167" stroke="{t["line"]}"/>',
        '<circle cx="38" cy="38" r="6" fill="#FF5F57"/>'
        '<circle cx="59" cy="38" r="6" fill="#FEBC2E"/>'
        '<circle cx="80" cy="38" r="6" fill="#28C840"/>',
        f'<text x="590" y="43" text-anchor="middle" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
        'letter-spacing=".4">profile.sh --live</text>',
        f'<rect x="35" y="88" width="418" height="472" rx="6" fill="{t["panel2"]}" '
        f'stroke="{t["line"]}"/>',
        f'<path d="M35 124H453" stroke="{t["line"]}"/>',
        f'<text x="49" y="111" fill="{t["chrome"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
        'font-weight="700" letter-spacing="1.2">VISUAL.MAP</text>',
        f'<text x="438" y="111" text-anchor="end" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">300×340 / 1-BIT</text>',
        f'<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 539h12M49 539v-12'
        f'M439 539h-12M439 539v-12" fill="none" stroke="{t["chrome"]}" opacity=".55"/>',
        '<g clip-path="url(#visualClip)" shape-rendering="crispEdges">',
        '<g opacity="1">',
    ]

    ai_centroid = ai.mean(axis=0)
    band_ids = rng.integers(0, 94, size=len(portrait))
    noise = rng.normal(0, 4, size=(94, 2))
    for band in range(94):
        pts = portrait[band_ids == band]
        if not len(pts):
            continue
        centroid = pts.mean(axis=0)
        delta = (ai_centroid - centroid) * 0.18 + noise[band]
        d = point_path(pts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{t["portrait"]}" stroke-width="1" '
            'opacity=".94">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="0 0;0 0;{num(delta[0])} {num(delta[1])};'
            f'{num(delta[0])} {num(delta[1])};0 0;0 0;0 0;0 0;0 0"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            'values=".94;.94;0;0;0;0;0;0;.94"/></path>'
        )

    for i in range(n):
        positions = animate_values(frames, i)
        parts.append(
            f'<path d="M-.65-.65h1.3v1.3h-1.3z" fill="{t["portrait"]}">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="{positions}"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{key_times}" '
            f'values="{opacity_values}"/></path>'
        )
    parts.append("</g>")

    intro_ids = rng.integers(0, 60, size=len(portrait))
    order = rng.permutation(60)
    starts = np.empty(60)
    starts[order] = np.linspace(0.05, 1.2, 60)
    for group in range(60):
        pts = portrait[intro_ids == group]
        if not len(pts):
            continue
        parts.append(
            f'<path d="{point_path(pts)}" fill="none" stroke="{t["portrait"]}" '
            'stroke-width="1" opacity="0">'
            f'<animate attributeName="opacity" begin="{num(starts[group])}s" dur=".8s" '
            'values="0;1" fill="freeze"/>'
            '<animate attributeName="opacity" begin="3.08s" dur=".12s" values="1;0" fill="freeze"/>'
            "</path>"
        )
    parts.extend(
        [
            "</g>",
            f'<text x="58" y="551" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10">'
            f'PTS {len(portrait):05d} · FS/SERPENTINE</text>',
            f'<rect x="474" y="88" width="672" height="472" rx="6" fill="{t["panel2"]}" '
            f'stroke="{t["line"]}"/>',
            f'<path d="M474 124H1146" stroke="{t["line"]}"/>',
            f'<text x="490" y="111" fill="{t["chrome"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
            'font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text>',
            '<g filter="url(#glow)"><circle cx="893" cy="106" r="4" fill="#FF4D5A">'
            '<animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/>'
            '</circle></g>',
            '<text x="905" y="111" fill="#FF4D5A" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="12" '
            'font-weight="700">LIVE</text>',
            f'<rect x="954" y="94" width="174" height="24" rx="12" fill="{t["chrome"]}" opacity=".16" '
            f'stroke="{t["chrome"]}"/>',
            f'<text x="1041" y="111" text-anchor="middle" fill="{t["chrome"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14" '
            'font-weight="700">@riccardoponte</text>',
        ]
    )

    value_right = 1127.0
    row_y = 153.0
    for label, value in ROWS:
        value_len = text_width(value, 14)
        label_len = text_width(label, 14)
        leader_start = 491 + label_len + 12
        leader_end = value_right - value_len - 12
        parts.extend(
            [
                f'<text x="491" y="{num(row_y)}" fill="{t["muted"]}" '
                'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14">'
                f"{html.escape(label)}</text>",
                f'<path d="{dotted_leader(leader_start, leader_end, row_y - 4)}" '
                f'fill="none" stroke="{t["line"]}" stroke-width="1" shape-rendering="crispEdges"/>',
                f'<text x="{num(value_right)}" y="{num(row_y)}" text-anchor="end" '
                f'fill="{t["text"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
                f'font-size="14" textLength="{num(value_len)}" lengthAdjust="spacingAndGlyphs">'
                f"{html.escape(value)}</text>",
            ]
        )
        row_y += 24.5

    parts.extend(
        [
            f'<path d="M490 530H1130" stroke="{t["line"]}"/>',
            f'<text x="491" y="548" fill="{t["accent"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
            "● ALL SYSTEMS NOMINAL</text>",
            f'<text x="1128" y="548" text-anchor="end" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
            "UTC+1 · MILANO NODE</text>",
            "</svg>",
        ]
    )
    return "".join(parts)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source portrait: {SOURCE}")
    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    logos = make_logos()

    portraits: dict[str, np.ndarray] = {}
    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + index)
        points = portrait_points(theme, rng)
        portraits[theme] = points
        np.save(DATA / f"portrait-{theme}.npy", points)

    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + 100 + index)
        sampled = {
            name: sample_logo_points(image, rng, TRAVELLER_COUNT)
            for name, image in logos.items()
        }
        for name, points in sampled.items():
            np.save(DATA / f"{name}-{theme}.npy", points)
        svg = render_svg(theme, portraits[theme], sampled, rng)
        output = ASSETS / f"banner-{theme}.v1.svg"
        output.write_text(svg, encoding="utf-8")
        byte_size = output.stat().st_size
        print(
            f"{output.relative_to(ROOT)}: {byte_size:,} bytes "
            f"({byte_size / 1024:.1f} KiB), {len(portraits[theme]):,} portrait dots, "
            f"{TRAVELLER_COUNT} travellers"
        )

    for name in logos:
        output = LOGOS / f"{name}.png"
        print(f"{output.relative_to(ROOT)}: {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

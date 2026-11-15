"""Cut the flat Odyssey illustrations into layers that can move on their own.

The art is blue or black ink on cream paper. For each picture this script:

1. Estimates the bare paper under the ink. Ink pixels are filled with a blur of
   the nearby paper pixels, so the paper keeps its mottled texture
   (`paper.webp`, opaque).
2. Turns "how much darker than the paper" into transparency (a colour key), and
   recovers the ink colour under that transparency. Paper becomes see-through,
   ink stays solid.
3. Gives every ink pixel to exactly one layer, using the rules in `PICTURES`
   (first rule that matches wins). Because no pixel is in two layers, the layers
   stacked at rest reproduce the original picture.
4. Saves each layer as a full-size WebP with transparency, so every layer of a
   picture stacks at the same position and size.

Portraits are different: they already have a transparent outside, so they are
split by radius into the Greek-key ring and the face disc.

Run from `frontend/`:
    uv run --with pillow --with numpy python scripts/odyssey-layers/split.py

Prints, per picture, how far the stacked layers are from the original.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / "public" / "images" / "odyssey"
OUT = ROOT / "layers"

# A rule: (layer name, region, colour filter). Region is (x0, y0, x1, y1) in
# source pixels, or None for "anywhere". Colour filter is "blue", "black" or None.
# "discard" drops the pixels (used for the speech cloud, which becomes its own
# layer through a separate rule order). "rest" catches everything unmatched.
PICTURES: dict[str, dict] = {
    "hero": {
        "src": "hero-background.png",
        "rules": [
            ("helmet", (150, 370, 520, 840), "black"),
            # The sail lines are thin and read as blue, so take everything above
            # the wave line, then only black ink (the hull) inside the waves.
            ("ship", (510, 650, 790, 880), None),
            ("ship", (495, 880, 800, 935), "black"),
            # The big wave crest overlaps the left column from y=290 down.
            ("columnLeft", (0, 90, 215, 290), "blue"),
            ("columnLeft", (0, 290, 50, 640), "blue"),
            ("columnRight", (1350, 90, 1536, 720), "blue"),
            ("land", (800, 660, 1536, 905), "blue"),
        ],
        "rest": "waves",
    },
    "intro": {
        "src": "intro-background.png",
        "rules": [
            ("meander", (0, 735, 1774, 815), None),
            ("hermes", (0, 60, 740, 735), None),
            ("amphora", (1440, 260, 1774, 735), "black"),
            ("olivesTop", (1260, 80, 1774, 400), "blue"),
            ("olivesLow", (1260, 400, 1774, 735), "blue"),
        ],
        "rest": "rest",
    },
    "footer": {
        "src": "leaderboard-footer-background.png",
        "rules": [
            ("meander", (0, 10, 1536, 75), None),
            ("oliveLeft", (90, 75, 300, 230), None),
            ("oliveRight", (1240, 75, 1450, 230), None),
            ("band", (0, 685, 1536, 750), None),
            ("ship", (580, 750, 900, 935), None),  # includes the blue pennant
            ("ship", (580, 935, 900, 1000), "black"),
        ],
        "rest": "sea",
        "tile": {"layer": "band", "y0": 685, "y1": 750},
    },
    "scene-temple": {
        "src": "scenes/legendary-scenes-temple.png",
        "rules": [
            ("sun", (780, 75, 1095, 390), None),
            ("mountains", (600, 430, 1536, 618), None),
        ],
        "rest": "front",
    },
    "scene-arena": {
        "src": "scenes/your-games-arena.png",
        "rules": [
            ("flag1", (342, 45, 485, 130), None),
            ("flag2", (598, 170, 718, 240), None),
            ("flag3", (898, 190, 1028, 255), None),
            ("flag4", (1238, 105, 1375, 175), None),
            ("cypressLeft", (0, 30, 215, 700), None),
            ("cypressRight", (1405, 140, 1536, 1024), None),
        ],
        "rest": "arena",
    },
}

# The four bot feature pictures share one layout: figure on the left, speech
# cloud top right, waves and a Greek-key border along the bottom.
for bot in ("telemachus", "menelaus", "odysseus", "poseidon"):
    PICTURES[f"{bot}-feature"] = {
        "src": f"bots/{bot}-feature.png",
        "rules": [
            ("cloud", (675, 10, 1819, 420), None),
        ],
        "rest": "figure",
        # Waves from this row down go to a front layer that is filled opaque
        # below its top edge, so the figure can sink behind it.
        "front": {"layer": "waves", "y0": 548},
    }


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _box(arr: np.ndarray, r: int, axis: int) -> np.ndarray:
    """Mean over a window of 2r+1 along one axis, edges clamped."""
    pad = [(0, 0)] * arr.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(arr, pad, mode="edge"), axis=axis, dtype=np.float64)
    n = arr.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def blur(arr: np.ndarray, radius: float) -> np.ndarray:
    """Near-Gaussian blur: three box blurs per axis (works on any float array)."""
    r = max(1, int(round(radius / 1.7)))
    out = arr.astype(np.float32)
    for _ in range(3):
        out = _box(_box(out, r, 0), r, 1)
    return out


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def key_ink(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (paper, alpha, ink colour) for an RGB float image (0-255)."""
    lum = luminance(rgb)
    # Paper pixels: bright and close to cream. Fill the rest from nearby paper.
    is_paper = (lum > 200).astype(np.float32)
    weight = blur(is_paper, 18) + 1e-4
    paper = blur(rgb * is_paper[..., None], 18) / weight[..., None]
    # A few tiny holes remain where ink is very dense; widen once more.
    weight2 = blur(is_paper, 60) + 1e-4
    paper_far = blur(rgb * is_paper[..., None], 60) / weight2[..., None]
    paper = np.where((weight < 0.02)[..., None], paper_far, paper)

    paper_lum = luminance(paper)
    raw = (paper_lum - lum) / np.maximum(paper_lum - 30.0, 1.0)
    alpha = smoothstep(0.07, 0.85, raw)
    safe = np.maximum(alpha, 1e-3)[..., None]
    ink = np.clip((rgb - (1 - alpha[..., None]) * paper) / safe, 0, 255)
    return paper, alpha, ink


def colour_class(ink: np.ndarray) -> np.ndarray:
    """True where the recovered ink is blue rather than black."""
    return (ink[..., 2] - ink[..., 0]) > 45


def save_rgba(path: Path, rgb: np.ndarray, alpha: np.ndarray, quality: int = 82) -> None:
    rgba = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path, "WEBP", quality=quality, alpha_quality=90, method=6)


def tile_period(alpha_band: np.ndarray) -> int:
    """Horizontal repeat length of a pattern band, by autocorrelation."""
    profile = alpha_band.mean(axis=0)
    profile = profile - profile.mean()
    best, best_lag = -1.0, 0
    for lag in range(30, 200):
        a, b = profile[:-lag], profile[lag:]
        score = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))
        if score > best:
            best, best_lag = score, lag
    return best_lag


def split_picture(name: str, spec: dict) -> None:
    src = Image.open(ROOT / spec["src"]).convert("RGB")
    rgb = np.asarray(src, dtype=np.float32)
    h, w = rgb.shape[:2]
    paper, alpha, ink = key_ink(rgb)
    blue = colour_class(ink)

    out_dir = OUT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8)).save(
        out_dir / "paper.webp", "WEBP", quality=70, method=6
    )

    owner = np.full((h, w), -1, dtype=np.int16)
    names: list[str] = []
    ys, xs = np.mgrid[0:h, 0:w]

    front = spec.get("front")
    if front:
        # Top edge of the waves per column, searched from y0 down.
        y0 = front["y0"]
        dense = alpha[y0:, :] > 0.5
        first = np.where(dense.any(axis=0), dense.argmax(axis=0) + y0, h)
        front_mask = ys >= first[None, :]
        names.append(front["layer"])
        owner[front_mask] = 0

    for layer, region, colour in spec["rules"]:
        mask = owner == -1
        if region is not None:
            x0, y0, x1, y1 = region
            mask &= (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
        if colour == "blue":
            mask &= blue
        elif colour == "black":
            mask &= ~blue
        if layer not in names:
            names.append(layer)
        owner[mask] = names.index(layer)
    owner[owner == -1] = len(names)
    names.append(spec["rest"])

    recon = paper.copy()
    for index, layer in enumerate(names):
        mine = owner == index
        layer_alpha = np.where(mine, alpha, 0.0)
        layer_rgb = ink
        if front and layer == front["layer"]:
            # Opaque below the wave edge: paper where there is no ink.
            layer_rgb = np.where(mine[..., None], rgb, ink)
            layer_alpha = np.where(mine, 1.0, 0.0)
        if spec.get("tile", {}).get("layer") == layer:
            save_tiled_band(out_dir, layer_rgb, layer_alpha, spec["tile"], w)
        save_rgba(out_dir / f"{layer}.webp", layer_rgb, layer_alpha)
        recon = layer_rgb * layer_alpha[..., None] + recon * (1 - layer_alpha[..., None])

    err = np.abs(recon - rgb).mean()
    print(f"{name}: {', '.join(names)} | mean error vs original {err:.2f}/255")


def save_tiled_band(out_dir: Path, rgb: np.ndarray, alpha: np.ndarray, tile: dict, w: int) -> None:
    """Band strip plus one extra repeat on the right, for an endless sideways loop."""
    y0, y1 = tile["y0"], tile["y1"]
    band_rgb, band_alpha = rgb[y0:y1], alpha[y0:y1]
    period = tile_period(band_alpha)
    # Use whole repeats only, so the loop seam lands on a repeat boundary.
    usable = (w // period) * period
    strip_rgb = np.concatenate([band_rgb[:, :usable], band_rgb[:, :period]], axis=1)
    strip_alpha = np.concatenate([band_alpha[:, :usable], band_alpha[:, :period]], axis=1)
    save_rgba(out_dir / "band-strip.webp", strip_rgb, strip_alpha)
    (out_dir / "band-strip.txt").write_text(
        f"period={period} usable={usable} width={usable + period} height={y1 - y0} y0={y0}\n"
    )
    print(f"  band period {period}px, strip {usable + period}x{y1 - y0}")


# Radius (fraction of the disc) of the paper gap just inside each Greek-key ring,
# measured from a brightness-by-radius profile of each portrait.
RING_SPLIT = {"telemachus": 0.748, "menelaus": 0.758, "odysseus": 0.688, "poseidon": 0.758}


def split_portrait(bot: str) -> None:
    im = Image.open(ROOT / "bots" / f"{bot}.png").convert("RGBA")
    size = 640
    im = im.resize((size, size), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32)
    c = (size - 1) / 2
    ys, xs = np.mgrid[0:size, 0:size]
    r = np.hypot(xs - c, ys - c) / (size / 2)
    split = RING_SPLIT[bot]
    face_w = smoothstep(split + 0.006, split - 0.006, r)
    out_dir = OUT / "portraits"
    out_dir.mkdir(parents=True, exist_ok=True)
    for part, wgt in (("face", face_w), ("ring", 1 - face_w)):
        alpha = a[..., 3] / 255 * wgt
        save_rgba(out_dir / f"{bot}-{part}.webp", a[..., :3], alpha, quality=85)
    print(f"portrait {bot}: face + ring at r={split}")


def main() -> None:
    for name, spec in PICTURES.items():
        split_picture(name, spec)
    for bot in ("telemachus", "menelaus", "odysseus", "poseidon"):
        split_portrait(bot)


if __name__ == "__main__":
    main()

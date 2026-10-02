"""
Core logic: combine several gifs into one wide gif where all of them play at
the same time, placed side by side at their native aspect, then auto-compress
so the result stays under a target file size.

Reused by the Flask app (app.py). Can also be run standalone for testing.
"""

import io
import os
from PIL import Image

# Default: stay safely under Steam's 5 MB limit.
DEFAULT_MAX_BYTES = int(4.9 * 1024 * 1024)

# Compression "ladder", best quality first. Each tuple is:
#   (scale, fps, colors) -> overall size multiplier, frames/sec, palette size
ATTEMPTS = [
    (1.00, 20, 256),
    (1.00, 15, 256),
    (0.85, 15, 256),
    (0.85, 15, 192),
    (0.75, 15, 128),
    (0.75, 12, 128),
    (0.65, 12, 96),
    (0.60, 10, 64),
    (0.50, 10, 64),
    (0.45, 10, 48),
    (0.40, 8, 32),
]


def load_gif(path):
    """Return (frames_rgba, durations_ms), walking frames defensively.

    seek() is used instead of n_frames, which can raise on slightly malformed
    gifs under newer Pillow versions.
    """
    im = Image.open(path)
    frames = []
    durations = []
    i = 0
    while True:
        try:
            im.seek(i)
        except (EOFError, IndexError, OSError):
            break
        frames.append(im.convert("RGBA"))
        durations.append(im.info.get("duration", 100) or 100)
        i += 1
    if not frames:
        frames.append(im.convert("RGBA"))
        durations.append(100)
    return frames, durations


def _total(durations):
    return sum(durations)


def _frame_at(frames, durations, t_ms):
    """Pick the frame showing at time t within one loop."""
    loop = _total(durations)
    if loop <= 0:
        return frames[0]
    t = t_ms % loop
    acc = 0
    for frame, d in zip(frames, durations):
        acc += d
        if t < acc:
            return frame
    return frames[-1]


def _render(gifs, native_w, native_h, scale, fps, colors):
    """Render the composite at the given settings; return (P-frames, dur_ms)."""
    canvas_w = max(1, round(native_w * scale))
    canvas_h = max(1, round(native_h * scale))

    loops = [g["loop"] for g in gifs if g["loop"] > 0]
    timeline = max(loops) if loops else 1000
    frame_step_ms = 1000 / fps
    num_frames = max(1, round(timeline / frame_step_ms))

    bg = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    flat = []
    for i in range(num_frames):
        t = i * frame_step_ms
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        x = 0
        for g in gifs:
            frame = _frame_at(g["frames"], g["durations"], t)
            w = max(1, round(g["width"] * scale))
            h = max(1, round(g["height"] * scale))
            frame = frame.resize((w, h), Image.LANCZOS)
            y = (canvas_h - h) // 2
            canvas.paste(frame, (x, y), frame)
            x += w
        comp = Image.alpha_composite(bg, canvas).convert(
            "P", palette=Image.ADAPTIVE, colors=colors
        )
        flat.append(comp)
    return flat, round(frame_step_ms)


def combine_gifs(paths, max_bytes=DEFAULT_MAX_BYTES, progress=None):
    """Combine the gifs at `paths` into one wide animated gif.

    Returns (gif_bytes, info_dict). Walks the compression ladder and returns
    the first result that fits under `max_bytes`, or the smallest attempt if
    nothing fits. `progress` is an optional callable(str) for status messages.
    """
    def log(msg):
        if progress:
            progress(msg)

    if not paths:
        raise ValueError("No gif files were provided.")

    gifs = []
    for path in paths:
        frames, durations = load_gif(path)
        gifs.append({
            "frames": frames,
            "durations": durations,
            "loop": _total(durations),
            "width": frames[0].size[0],
            "height": frames[0].size[1],
        })
        log(f"Loaded {os.path.basename(path)}: {len(frames)} frames, "
            f"{frames[0].size[0]}x{frames[0].size[1]}")

    native_w = sum(g["width"] for g in gifs)
    native_h = max(g["height"] for g in gifs)
    log(f"Native canvas: {native_w}x{native_h} (ratio {native_w/native_h:.3f}:1)")

    best = None  # (size, bytes, info) fallback = smallest produced
    for scale, fps, colors in ATTEMPTS:
        flat, dur = _render(gifs, native_w, native_h, scale, fps, colors)
        buf = io.BytesIO()
        flat[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=flat[1:],
            duration=dur,
            loop=0,
            disposal=2,
            optimize=True,
        )
        data = buf.getvalue()
        size = len(data)
        w = max(1, round(native_w * scale))
        h = max(1, round(native_h * scale))
        mb = size / (1024 * 1024)
        info = {
            "width": w, "height": h, "frames": len(flat),
            "fps": fps, "colors": colors, "scale": scale,
            "bytes": size, "mb": round(mb, 2),
        }
        fit = size <= max_bytes
        log(f"scale={scale} fps={fps} colors={colors} -> "
            f"{w}x{h}, {len(flat)} frames, {mb:.2f} MB "
            f"[{'OK' if fit else 'too big'}]")
        if fit:
            return data, info
        if best is None or size < best[0]:
            best = (size, data, info)

    # Nothing fit; return the smallest attempt we produced.
    log("Could not get under the size limit; returning smallest attempt.")
    return best[1], best[2]


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args:
        print("usage: python combiner.py <gif1> <gif2> ... <output.gif>")
        sys.exit(1)
    out = args[-1]
    inputs = args[:-1] if len(args) > 1 else args
    data, info = combine_gifs(inputs, progress=print)
    with open(out, "wb") as f:
        f.write(data)
    print(f"saved {out}: {info}")

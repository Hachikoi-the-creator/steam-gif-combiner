# GIF Combiner

A small Flask webapp that takes several GIFs and stitches them into one **wide**
GIF where all of them play at the same time, side by side. The result is
auto-compressed to stay under **5 MB** (Steam's animated-showcase limit).

## Setup

```powershell
cd gif-combiner
python -m pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## How to use

1. Name your GIFs with numbers only, in order: `1.gif`, `2.gif`, `3.gif`, …,
   `n.gif`. The numbers must start at `1` and be consecutive (no gaps or
   duplicates). The order is the left-to-right order in the output.
2. Drag them onto the page (or click to browse) and press **Combine GIFs**.
3. Preview and download `combined.gif`.

## How it works

- All GIFs are placed side by side at their native size (no padding, so no
  white bars). Output height is the tallest input; shorter GIFs are centered.
- Every GIF animates on a shared timeline, looping to the longest input's cycle.
- Output is rendered through a quality ladder (resolution → fps → palette size)
  and the first result under the size limit is returned, so you keep the best
  quality that fits.

## Files

- `app.py` — Flask routes, upload validation, download.
- `combiner.py` — core combining + compression logic (also runnable standalone:
  `python combiner.py 1.gif 2.gif 3.gif out.gif`).
- `templates/index.html`, `static/style.css`, `static/app.js` — the UI.

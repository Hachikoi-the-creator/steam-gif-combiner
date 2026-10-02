"""
Steam Animated Showcase: upload several gifs (named 1.gif ... n.gif) and
download a single wide gif where all of them play at the same time,
auto-compressed under 5 MB so it fits a Steam profile artwork showcase.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""

import io
import re
import tempfile
import os
from flask import (
    Flask, render_template, request, send_file, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename

from combiner import combine_gifs, DEFAULT_MAX_BYTES

app = Flask(__name__)

# Accept a generous upload size (each gif can be a few MB). 100 MB total.
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

ALLOWED_EXT = {".gif"}
NAME_RE = re.compile(r"^(\d+)\.gif$", re.IGNORECASE)


def validate_and_order(files):
    """Validate uploaded files and return them ordered 1..n.

    Rules enforced:
      - every file must be a .gif
      - names must be integers: 1.gif, 2.gif, ...
      - numbers must start at 1 and be consecutive with no gaps/duplicates
    Returns (ordered_files, error_message). error_message is None on success.
    """
    if not files:
        return None, "No files were uploaded."

    numbered = {}
    for f in files:
        name = secure_filename(f.filename or "")
        m = NAME_RE.match(name)
        if not m:
            return None, (
                f'"{f.filename}" is not valid. Files must be GIFs named with '
                f"numbers only: 1.gif, 2.gif, 3.gif, ..."
            )
        n = int(m.group(1))
        if n in numbered:
            return None, f"Duplicate file number: {n}.gif appears more than once."
        numbered[n] = f

    nums = sorted(numbered.keys())
    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        return None, (
            "File numbers must start at 1 and be consecutive with no gaps. "
            f"Got: {', '.join(str(n) + '.gif' for n in nums)}. "
            f"Expected: {', '.join(str(n) + '.gif' for n in expected)}."
        )

    ordered = [numbered[n] for n in nums]
    return ordered, None


IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imgs")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/imgs/<path:filename>")
def imgs(filename):
    """Serve the tutorial screenshots in imgs/ (not under static/)."""
    return send_from_directory(IMG_DIR, filename)


@app.route("/combine", methods=["POST"])
def combine():
    files = request.files.getlist("gifs")
    ordered, error = validate_and_order(files)
    if error:
        return jsonify({"error": error}), 400

    # Save uploads to a temp dir, run the combiner, return the gif.
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, f in enumerate(ordered, start=1):
            p = os.path.join(tmp, f"{i}.gif")
            f.save(p)
            paths.append(p)

        try:
            data, info = combine_gifs(paths, max_bytes=DEFAULT_MAX_BYTES)
        except Exception as exc:  # noqa: BLE001 - surface a readable message
            return jsonify({"error": f"Failed to combine gifs: {exc}"}), 500

    resp = send_file(
        io.BytesIO(data),
        mimetype="image/gif",
        as_attachment=True,
        download_name="combined.gif",
    )
    # Expose render info so the UI can show details.
    resp.headers["X-Gif-Width"] = str(info["width"])
    resp.headers["X-Gif-Height"] = str(info["height"])
    resp.headers["X-Gif-Frames"] = str(info["frames"])
    resp.headers["X-Gif-Fps"] = str(info["fps"])
    resp.headers["X-Gif-Mb"] = str(info["mb"])
    resp.headers["Access-Control-Expose-Headers"] = (
        "X-Gif-Width,X-Gif-Height,X-Gif-Frames,X-Gif-Fps,X-Gif-Mb"
    )
    return resp

"""
tuto 1: Go to your steam profile in any web browser (chrome, firefox, brave), then click on Artwork
tuto 2: select upload artwork
tuto 3: Give it a name (it will appear in your profile), select the downloaded gif, select you own the gif
tuto 4: Go back to your profile, select edit profile
tuto 5: select showcase manager, whit the arrows in the left select a section you dont mind replacing, and in the higligted dropdown select featured artwork showcase, now just select the gif you uploaded, save, and enjoy!
"""

@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "Upload too large (100 MB max total)."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)

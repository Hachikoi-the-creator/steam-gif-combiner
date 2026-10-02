const fileInput = document.getElementById("fileInput");
const drop = document.getElementById("drop");
const fileList = document.getElementById("fileList");
const validation = document.getElementById("validation");
const submitBtn = document.getElementById("submitBtn");
const clearBtn = document.getElementById("clearBtn");
const form = document.getElementById("form");
const resultCard = document.getElementById("result");
const resultImg = document.getElementById("resultImg");
const resultMeta = document.getElementById("resultMeta");
const downloadLink = document.getElementById("downloadLink");
const btnLabel = submitBtn.querySelector(".btn-label");
const spinner = submitBtn.querySelector(".spinner");

const NAME_RE = /^(\d+)\.gif$/i;
let selected = []; // array of File

function fmtSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function setValidation(msg, kind) {
  if (!msg) {
    validation.hidden = true;
    validation.textContent = "";
    validation.className = "validation";
    return;
  }
  validation.hidden = false;
  validation.textContent = msg;
  validation.className = "validation " + (kind || "");
}

// Returns { ok, error } after checking names are 1..n consecutive gifs.
function validate(files) {
  if (files.length === 0) return { ok: false, error: "" };

  const nums = [];
  for (const f of files) {
    const m = NAME_RE.exec(f.name);
    if (!m) {
      return {
        ok: false,
        error: `"${f.name}" is not valid. Files must be GIFs named with numbers only: 1.gif, 2.gif, 3.gif, …`,
      };
    }
    nums.push(parseInt(m[1], 10));
  }
  nums.sort((a, b) => a - b);
  for (let i = 0; i < nums.length; i++) {
    if (nums[i] !== i + 1) {
      const got = nums.map((n) => n + ".gif").join(", ");
      const exp = nums.map((_, i) => i + 1 + ".gif").join(", ");
      if (new Set(nums).size !== nums.length) {
        return { ok: false, error: `Duplicate file numbers found. Got: ${got}.` };
      }
      return {
        ok: false,
        error: `Numbers must start at 1 and be consecutive. Got: ${got}. Expected: ${exp}.`,
      };
    }
  }
  return { ok: true, error: "" };
}

function render() {
  fileList.innerHTML = "";
  const { ok, error } = validate(selected);

  // Sort for display by numeric name when possible.
  const display = [...selected].sort((a, b) => {
    const ma = NAME_RE.exec(a.name);
    const mb = NAME_RE.exec(b.name);
    if (ma && mb) return parseInt(ma[1], 10) - parseInt(mb[1], 10);
    return a.name.localeCompare(b.name);
  });

  display.forEach((f) => {
    const li = document.createElement("li");
    const m = NAME_RE.exec(f.name);
    if (!m) li.classList.add("bad");
    li.innerHTML = `
      <span class="num">${m ? m[1] : "?"}</span>
      <span class="fname">${f.name}</span>
      <span class="fsize">${fmtSize(f.size)}</span>`;
    fileList.appendChild(li);
  });

  clearBtn.hidden = selected.length === 0;

  if (selected.length === 0) {
    setValidation("", "");
    submitBtn.disabled = true;
    return;
  }
  if (!ok) {
    setValidation(error, "err");
    submitBtn.disabled = true;
  } else {
    setValidation(
      `${selected.length} GIF${selected.length > 1 ? "s" : ""} ready to combine.`,
      "ok"
    );
    submitBtn.disabled = false;
  }
}

function addFiles(fileListObj) {
  const incoming = Array.from(fileListObj);
  // De-dupe by name, newest wins.
  const byName = new Map(selected.map((f) => [f.name, f]));
  incoming.forEach((f) => byName.set(f.name, f));
  selected = Array.from(byName.values());
  render();
}

fileInput.addEventListener("change", (e) => addFiles(e.target.files));

["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.add("drag");
  })
);
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.remove("drag");
  })
);
drop.addEventListener("drop", (e) => {
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files);
});

clearBtn.addEventListener("click", () => {
  selected = [];
  fileInput.value = "";
  resultCard.hidden = true;
  render();
});

function setLoading(on) {
  submitBtn.disabled = on;
  spinner.hidden = !on;
  btnLabel.textContent = on ? "Combining…" : "Combine GIFs";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const { ok } = validate(selected);
  if (!ok) return;

  setLoading(true);
  resultCard.hidden = true;
  setValidation("Uploading and combining… this can take a moment.", "ok");

  try {
    const fd = new FormData();
    selected.forEach((f) => fd.append("gifs", f, f.name));

    const resp = await fetch("/combine", { method: "POST", body: fd });

    if (!resp.ok) {
      let msg = "Something went wrong.";
      try {
        const data = await resp.json();
        if (data.error) msg = data.error;
      } catch (_) {}
      setValidation(msg, "err");
      setLoading(false);
      return;
    }

    const w = resp.headers.get("X-Gif-Width");
    const h = resp.headers.get("X-Gif-Height");
    const frames = resp.headers.get("X-Gif-Frames");
    const fps = resp.headers.get("X-Gif-Fps");
    const mb = resp.headers.get("X-Gif-Mb");

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    resultImg.src = url;
    downloadLink.href = url;
    resultMeta.textContent =
      w && h
        ? `${w}×${h} · ${frames} frames · ${fps} fps · ${mb} MB`
        : "Your combined GIF is ready.";
    resultCard.hidden = false;
    setValidation("", "");
    resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    setValidation("Network error: " + err.message, "err");
  } finally {
    setLoading(false);
  }
});

render();

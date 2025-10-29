# DualCam Replay — Desktop Video Replay System (Python + PySide6 + OpenCV)

**DualCam Replay** is a desktop video replay system with **two cameras**, a **1-hour on-disk JPEG buffer**, frame-by-frame control, playback speeds (0.5x / 1x / 2x), reverse playback, clip export, and camera selection via the user interface.  
It focuses on **low latency**, **stability on Windows**, and a **responsive 1080p layout**.

---

## ✨ Features

- **On-disk buffer (1 hour)** per camera with **automatic cleanup** on exit.
- Ensures **1080p capture resolution**.
- **Camera selection dialog** on startup (auto-detects connected cameras).
- **No live mode** — everything is replayed from the buffer.
- **1-hour time slider** synchronized with playback.
- **Keyboard shortcuts**:
  - `←` / `→`: move **one frame backward / forward**
  - `,` / `.`: **reverse playback** / **normal playback**
  - `Q` / `W` / `E`: playback at **0.5x / 1x / 2x speed**
  - `Space`: pause/resume
  - `Backspace`: jump to **now − 5 seconds**
  - `1` / `2` / `3`: show **Camera 1**, **Camera 2**, or **both side-by-side**
  - `Enter`: export **three 20-second clips** — cam1, cam2, and both
- **Timestamped clip exports** (e.g. `clip_cam1_2025-10-29_23-58-12.mp4`)
- **Automatic fallback to AVI** if MP4 codec is unavailable
- **Modular, extensible architecture**

---

## 🧱 Project Structure

```
replay/
  __init__.py
  main.py            # Entry point (runnable via script)
  config.py          # Configuration (FPS, paths, codecs, 1080p, etc.)
  buffer.py          # On-disk JPEG buffer + in-memory index + cleanup
  capture.py         # Camera capture threads (OpenCV) + scanning
  export.py          # MP4/AVI clip export
  widgets.py         # UI components (image pane, camera selection dialog)
  ui.py              # Main window, playback logic, and shortcuts
exports/             # Runtime folder for exported clips
buffer_jpeg/         # Runtime frame buffer (auto-deleted on exit)
pyproject.toml
run.py               # Quick launcher script
```

---

## 🖥️ Requirements

- **Python 3.10+**
- **Windows** recommended (uses `CAP_DSHOW`), but compatible with Linux/macOS.
- Dependencies:
  - `PySide6` (UI)
  - `opencv-python` (capture and encoding)
  - `numpy`

> Ensure your webcam drivers and codecs support MP4 writing.

---

## ⚙️ Installation

```bash
# 1) (optional) create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

# 2) install in development mode
pip install -e .
```

---

## ▶️ Running

Two ways to launch:

```bash
# via console script (installed by pyproject.toml)
dualcam-replay

# or directly via Python
python run.py
```

A dialog will appear to select **two cameras**.  
If no selection is made, the default indices `(0, 1)` will be used.

---

## ⌨️ Keyboard Shortcuts

| Key          | Action                                       |
|---------------|----------------------------------------------|
| `1`           | Show **Camera 1** full-screen                |
| `2`           | Show **Camera 2** full-screen                |
| `3`           | Show **both cameras** side-by-side           |
| `Space`       | **Pause / Resume playback**                  |
| `Backspace`   | Jump to **now − 5 seconds**                  |
| `←` / `→`     | **Step backward / forward one frame**        |
| `,` / `.`     | **Reverse / Normal playback**                |
| `Q` / `W` / `E` | Playback speed: **0.5x / 1x / 2x**         |
| `Enter`       | Export **three 20-second clips** (cam1, cam2, both) |

> The **slider** navigates through the full **1-hour buffer**.

---

## 🧠 How It Works

- **Capture Threads**: two OpenCV threads save 1080p frames as JPEG files to disk at `WRITE_FPS` (default 20 FPS).
- **Buffer**: each camera maintains a memory index of `(timestamp, path)`. Once full, old frames are deleted automatically.
- **Playback**: the UI computes a `play_ts` timestamp and fetches the nearest frame.  
  Controls modify `play_ts` (frame-by-frame, reverse, forward, speed control).
- **Export (Enter)**: creates **three 20-second clips** ending at the current `play_ts` (usually paused).  
  MP4 (`mp4v`) is attempted first, falling back to AVI (`MJPG`) if needed.

---

## ⚙️ Configuration

Adjust parameters in `replay/config.py`:

| Parameter | Default | Description |
|------------|----------|-------------|
| `BUFFER_SECONDS` | `60 * 60` | Total buffer time (1 hour) |
| `WRITE_FPS` | 20 | Frame write rate to disk |
| `PLAYBACK_FPS` | 30 | UI and export playback rate |
| `JPEG_QUALITY` | 80 | JPEG compression quality |
| `CAPTURE_SIZE` | `(1920, 1080)` | Capture resolution |
| `EXPORT_SIZE` | `(1920, 1080)` | Output video resolution |
| `FOURCC_MP4` / `FOURCC_AVI` | `"mp4v"` / `"MJPG"` | Video codecs |
| `SCAN_RANGE` | 11 | Camera scanning range |

---

## 🧹 Buffer Cleanup

- When the app **closes**, capture threads are stopped and the `buffer_jpeg/` directory is **permanently deleted**.
- A fallback cleanup is also registered with `atexit`.
- Exported clips remain in `exports/`.

> For privacy-sensitive setups, redirect `EXPORT_DIR` to a secure or encrypted location.

---

## 📈 Performance Tips

- Prefer **SSD storage** for smoother buffer performance.
- Lower `WRITE_FPS` or `PLAYBACK_FPS` on slower CPUs.
- For USB 2.0 cameras, 1080p@30 may be unreliable—use 720p or lower FPS if needed.
- Windows is preferred for consistent DirectShow performance.

---

## 🛠️ Troubleshooting

| Problem | Possible Fix |
|----------|---------------|
| Black screen / no image | Verify camera indices and permissions. |
| MP4 export fails | Your OpenCV build may lack H.264 support — AVI fallback is automatic. |
| Playback lag | Lower FPS or close other webcam-using apps. |
| Linux/macOS | Switch OpenCV backend (e.g., `CAP_V4L2` on Linux). |

---

## 🗺️ Roadmap

- Optional **audio capture** from external line-in.
- **Bookmarks** within buffer timeline.
- “Both” view option with **fill+crop** (no letterbox).
- Support for **N cameras** with unified control.
- **FFmpeg export** for improved codec compatibility.

---

## 🤝 Contributing

1. Fork this repository and create a feature branch:  
   `git checkout -b feat/my-feature`
2. Follow the existing code style and **document** new options.
3. Submit a pull request with a clear description and rationale.

---

## 📄 License

Choose a license for your project (e.g., MIT, Apache-2.0).  
Include it as `LICENSE` in the repository root.

---

## 📬 Contact

Feel free to open an **Issue** for bugs, suggestions, or improvements.  
Contributions are very welcome!

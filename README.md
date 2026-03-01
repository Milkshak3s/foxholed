# Foxholed

Real-time map position reader for [Foxhole](https://www.foxholegame.com/).
Captures your game window, detects which map region you're in via template
matching (or OCR fallback), and displays your position on an interactive hex
map.

Works on **Windows** and **Linux**.

## Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (optional, used as fallback)
- **Linux only:** `xdotool` (`sudo apt install xdotool`)

## Installation

```bash
uv sync
```

## Quick start

```bash
uv run python -m foxholed
```

The app window will open with:

- A **toolbar** at the top with a window picker dropdown, a Refresh button, and
  a capture interval spinner.
- A **hex map** in the center showing all Foxhole regions.
- A **status bar** at the bottom showing the detected region and confidence.

### 1. Select your game window

The **Window** dropdown lists all visible windows on your system. Pick the
Foxhole game window (it defaults to `"War"`). Click **Refresh** to re-scan if
you launched the game after opening Foxholed. You can also type a custom window
title directly into the dropdown.

### 2. Add region templates

Foxholed identifies your position by matching the in-game minimap against
template images. Out of the box the `assets/templates/` directory is empty, so
you need to create templates:

1. In Foxhole, open your map and navigate to a region.
2. Take a screenshot and crop **just the minimap area** (the small map in the
   corner of the game window, not the full-screen map).
3. Save it as a PNG in `assets/templates/` with the **exact region name** as
   the filename.

Example filenames:

```
assets/templates/Deadlands.png
assets/templates/Stonecradle.png
assets/templates/The Heartlands.png
assets/templates/Oarbreaker Isles.png
```

The filename (minus `.png`) must match a region name from the game. The full
list of supported regions is in `src/foxholed/map_data.py`.

**Tips:**

- Templates are loaded as grayscale — color doesn't matter.
- Keep templates **smaller than** the minimap crop region (default 300x300 px).
- The more regions you add templates for, the better detection coverage.

### 3. Adjust settings

| Setting            | Where                  | Default | Description                                    |
| ------------------ | ---------------------- | ------- | ---------------------------------------------- |
| Window title       | Toolbar dropdown       | `War`   | Title of the game window to capture             |
| Capture interval   | Toolbar spinner        | 1000 ms | How often to capture and analyse the minimap    |
| Confidence threshold | `Config` in code     | 70%     | Minimum template match score to accept          |
| Minimap region     | `Config` in code       | 300x300 at (0,0) | Pixel area to crop from the game window |

## How detection works

Each tick (default every 1 second):

1. **Capture** — finds your game window by title and grabs a screenshot.
2. **Crop** — extracts the minimap region from the screenshot.
3. **Template match** — compares the cropped minimap against every template in
   `assets/templates/` using OpenCV's `matchTemplate`. The best match above the
   confidence threshold wins.
4. **OCR fallback** — if no template matches, attempts to read region text from
   the minimap using Tesseract OCR.
5. **Display** — highlights the detected region on the hex map and shows
   confidence in the status bar.

## Development

```bash
# Run tests
uv run python -m pytest tests/ -v
```

## Platform notes

### Windows

Window detection and enumeration use the Win32 API via `ctypes` — no extra
dependencies needed.

### Linux

Requires `xdotool` for window detection and enumeration:

```bash
sudo apt install xdotool
```

# FWinPhotoViewer

, built with PyQt6 and Pillow. Designed as a better alternative to Windows Photo Viewer, with support for favorites, HEIC/HEIF formats, and batch export.

## Features

- **Browse Images:** Quickly open a folder and view all supported images (.jpg, .jpeg, .png, .webp, .bmp, .gif, .heic, .heif).
- **Favorites:** Mark/unmark images as favorites
- **Export Favorites:** Export only favorite images from the currently selected folder to a destination of your choice. Handles filename collisions.
- **Touch & Gestures:** Pinch-to-zoom and scroll support for touchscreens.
- **Keyboard Shortcuts:**
  - Left/Right arrows: Previous/Next image
  - F or Space: Toggle favorite
  - Ctrl+O: Open folder
  - Ctrl+E: Export favorites
- **Resizable & Zoomable:** Double-click to toggle fit-to-window/100% view. Mouse wheel and pinch gestures for zoom.

## Installation (Windows)

### Option 1: Download from Releases

1. Go to the [Releases](https://github.com/yourusername/FWinPhotoViewer/releases) page.
2. Download the latest `FWinPhotoViewer.exe`.
3. Place it anywhere (e.g. Desktop, Programs folder).
4. Run it — no installation required.

### Option 2: Build & Run Locally (Optional)

1. Install [Python 3.10+](https://www.python.org/downloads/).
2. Clone or download this repository.
3. Install dependencies:

```bash
  pip install -r requirements.txt
```

4. Run the app:

```bash
  python app.py
```

5. (Optional) Build a standalone executable with PyInstaller:

```bash
  pyinstaller --onefile --windowed app.py --icon=assets/icon.ico --add-data "assets/icon.ico;assets"
```

## Usage

- **Open Folder:** Click the folder icon or press Ctrl+O to select a folder of images.
- **Navigate:** Use arrow keys or toolbar buttons to move between images.
- **Favorite:** Click the large star/heart button or press F/Space to mark/unmark as favorite.
- **Export:** Click "Export Favorites" or press Ctrl+E to copy favorite images from the current folder to another location.

## Data & Privacy

- Favorites are stored in `favorites.json` in your AppData folder (`%APPDATA%/FWinPhotoViewer/favorites.json`).

## Supported Formats

- JPEG, PNG, WebP, BMP, GIF, HEIC, HEIF

## Troubleshooting

- If HEIC/HEIF images do not load, ensure `pillow-heif` is installed.
- For missing icons or UI issues, check that `assets/icon.ico` exists and is referenced correctly.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Credits

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/intro), [Pillow](https://python-pillow.org/), and [pillow-heif](https://github.com/carsales/pillow-heif).

## Screenshots

*(Add screenshots of the app UI here)*

---

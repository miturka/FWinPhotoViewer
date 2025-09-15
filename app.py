import json
import shutil
from pathlib import Path
import sys
from PIL import Image, ExifTags

from PyQt6.QtCore import Qt, QRectF, QStandardPaths
from PyQt6.QtGui import QAction, QImageReader, QPixmap, QImage, QTransform, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QToolBar, QStatusBar,
    QGraphicsView, QGraphicsScene, QMessageBox, QStyle
)
import pillow_heif

pillow_heif.register_heif_opener()

def get_appdata_dir() -> Path:
    # Roaming AppData on Windows, ~/.local/share on Linux, ~/Library/Application Support on macOS
    loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    appdir = Path(loc) / "FWinPhotoViewer"
    appdir.mkdir(parents=True, exist_ok=True)
    return appdir

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic", ".heif"}
FAV_FILE = get_appdata_dir() / "favorites.json"


def _apply_exif_orientation(path: Path, qimg: QImage) -> QImage:
    """
    Reads the EXIF orientation tag (if present) and returns a rotated/flipped QImage.
    If there is no orientation info, returns the image unchanged.
    """
    try:
        with Image.open(path) as pil_img:
            exif = pil_img._getexif() or {}
            for tag, val in exif.items():
                if ExifTags.TAGS.get(tag) == "Orientation":
                    orientation = val
                    transform = QTransform()
                    if orientation == 2:   # Mirrored left-right
                        transform.scale(-1, 1)
                    elif orientation == 3: # Rotated 180
                        transform.rotate(180)
                    elif orientation == 4: # Mirrored top-bottom
                        transform.scale(1, -1)
                    elif orientation == 5: # Mirrored along top-left diagonal
                        transform.scale(-1, 1)
                        transform.rotate(90)
                    elif orientation == 6: # Rotated 270 CW
                        transform.rotate(90)
                    elif orientation == 7: # Mirrored along top-right diagonal
                        transform.scale(-1, 1)
                        transform.rotate(-90)
                    elif orientation == 8: # Rotated 90 CW
                        transform.rotate(-90)
                    if not transform.isIdentity():
                        qimg = qimg.transformed(transform)
                    break
    except Exception:
        pass
    return qimg


def pil_to_qimage(pil_image: Image.Image) -> QImage:
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
    return qimg

def load_image(path: Path) -> QPixmap | None:
    ext = path.suffix.lower()
    if ext in [".heic", ".heif"]:
        try:
            with Image.open(path) as im:
                im.load()
                qimg = pil_to_qimage(im)
                qimg = _apply_exif_orientation(path, qimg)
                return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"HEIC load failed: {e}")
            return None
    else:
        reader = QImageReader(str(path))
        img = reader.read()
        if img.isNull():
            return None
        img = _apply_exif_orientation(path, img)
        return QPixmap.fromImage(img)


class ImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.pixmap_item = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._fit_mode = True
        self._base_pixmap = None

        # Optional: enable pinch gesture on touch devices (works on many Windows touchscreens)
        self.grabGesture(Qt.GestureType.PinchGesture)

    def set_pixmap(self, pixmap: QPixmap | None):
        self.scene().clear()
        self.pixmap_item = None
        self._base_pixmap = pixmap
        if pixmap is None:
            return

        self.pixmap_item = self.scene().addPixmap(pixmap)
        self.scene().setSceneRect(QRectF(self.pixmap_item.pixmap().rect()))
        self.resetTransform()
        if self._fit_mode:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        if self._base_pixmap is None:
            return
        # Zoom with mouse wheel or trackpad
        zoom_in = event.angleDelta().y() > 0
        factor = 1.25 if zoom_in else 1 / 1.25
        self._fit_mode = False
        self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_mode and self._base_pixmap is not None:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event):
        # Toggle fit-to-window / 100% on double click
        if self._base_pixmap is None:
            return
        if self._fit_mode:
            self._fit_mode = False
            self.resetTransform()
        else:
            self._fit_mode = True
            self.resetTransform()
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().mouseDoubleClickEvent(event)

    def event(self, e):
        # Basic pinch gesture support (if touch is available)
        if e.type() == 198:  # QEvent.Gesture
            gesture = e.gesture(Qt.GestureType.PinchGesture)
            if gesture and self._base_pixmap is not None:
                change_flags = int(gesture.changeFlags())
                if change_flags & 1:  # ScaleFactorChanged
                    self._fit_mode = False
                    self.scale(gesture.scaleFactor(), gesture.scaleFactor())
                return True
        return super().event(e)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FWinPhotoViewer")
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)  # folder where PyInstaller unpacks
        else:
            base = Path(__file__).resolve().parent
        self.setWindowIcon(QIcon(str(base / "assets" / "icon.ico")))
        self.viewer = ImageView()
        self.setCentralWidget(self.viewer)
        self.setStatusBar(QStatusBar())

        self.folder = None
        self.files: list[Path] = []
        self.index = -1
        self.favorites: set[Path] = set()

        self._load_favorites()
        self._build_toolbar()
        self._update_ui_state()

    # ---------- Toolbar / Actions ----------
    def _build_toolbar(self):
        from PyQt6.QtWidgets import QToolButton
        from PyQt6.QtGui import QFont
        tb = QToolBar("Main")
        self.addToolBar(tb)

        open_act = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "Open Folder", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self.choose_folder)
        tb.addAction(open_act)

        prev_act = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack), "Previous", self)
        prev_act.setShortcut("Left")
        prev_act.triggered.connect(self.prev_image)
        tb.addAction(prev_act)

        next_act = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward), "Next", self)
        next_act.setShortcut("Right")
        next_act.triggered.connect(self.next_image)
        tb.addAction(next_act)

        self.fav_btn = QToolButton(self)
        self.fav_btn.setText("♡")
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.fav_btn.setFont(font)
        self.fav_btn.setToolTip("Favorite (F)")
        self.fav_btn.setShortcut = lambda x: None  # Dummy to avoid errors
        self.fav_btn.clicked.connect(self.toggle_favorite)
        tb.addWidget(self.fav_btn)

        export_act = QAction("Export Favorites…", self)
        export_act.setShortcut("Ctrl+E")
        export_act.triggered.connect(self.export_favorites)
        tb.addAction(export_act)

    # ---------- File ops ----------
    def choose_folder(self):
        start_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder of photos", start_dir)
        if not folder:
            return

        self.folder = Path(folder)
        self.files = sorted(
            [p for p in self.folder.rglob("*") if p.suffix.lower() in IMAGE_EXTS and p.is_file()]
        )
        if not self.files:
            QMessageBox.information(self, "No images", "No supported images found in that folder.")
            return

        self.index = 0
        self._show_current()
    
    def _update_fav_icon(self):
        """Update the toolbar button to show a big ♥ or ♡ depending on current photo."""
        if not self.files or self.index < 0:
            self.fav_btn.setText("♡")
            return
        path = self.files[self.index]
        if path in self.favorites:
            self.fav_btn.setText("♥")
        else:
            self.fav_btn.setText("♡")

    def _show_current(self):
        if self.index < 0 or self.index >= len(self.files):
            return
        path = self.files[self.index]
        pix = load_image(path)
        if pix is None:
            self.statusBar().showMessage(f"Failed to load: {path.name}")
            return
        self.viewer.set_pixmap(pix)
        # self.setWindowTitle(f"FWinPhotoViewer — {path.name}  [{self.index+1}/{len(self.files)}]  ({path})")
        self.setWindowTitle(f"FWinPhotoViewer - ({path}) [{self.index+1}/{len(self.files)}]")
        self.statusBar().showMessage(f"{self.index+1}/{len(self.files)} — {path}")
        self._update_fav_icon()   

    def next_image(self):
        if not self.files:
            return
        self.index = (self.index + 1) % len(self.files)
        self._show_current()

    def prev_image(self):
        if not self.files:
            return
        self.index = (self.index - 1) % len(self.files)
        self._show_current()

    # ---------- Favorites ----------
    def toggle_favorite(self):
        if not self.files or self.index < 0:
            return
        path = self.files[self.index]
        if path in self.favorites:
            self.favorites.remove(path)
        else:
            self.favorites.add(path)
        self._save_favorites()
        self._update_fav_icon()   
        self._show_current()    

    def _fav_json_payload(self):
        return {"favorites": [str(p.resolve()) for p in sorted(self.favorites)]}

    def _load_favorites(self):
        if FAV_FILE.exists():
            try:
                data = json.loads(FAV_FILE.read_text(encoding="utf-8"))
                favs = data.get("favorites", [])
                self.favorites = {Path(p) for p in favs}
            except Exception:
                self.favorites = set()

    def _save_favorites(self):
        try:
            FAV_FILE.write_text(json.dumps(self._fav_json_payload(), indent=2), encoding="utf-8")
        except Exception as e:
            QMessageBox.warning(self, "Save error", f"Could not save favorites.json: {e}")

    # ---------- Export ----------
    def export_favorites(self):
        if self.folder is None:
            QMessageBox.information(self, "No folder selected", "Please select a folder first.")
            return

        favs_in_folder = [p for p in self.favorites if p.parent.resolve() == self.folder.resolve()]
        if not favs_in_folder:
            QMessageBox.information(self, "No favorites in folder", "No favorite photos found in the selected folder.")
            return

        target = QFileDialog.getExistingDirectory(self, "Choose export folder")
        if not target:
            return
        target = Path(target)

        copied = 0
        for src in favs_in_folder:
            if not src.exists():
                continue
            dst = target / src.name
            if dst.exists():
                stem, suf = dst.stem, dst.suffix
                i = 1
                while True:
                    alt = target / f"{stem}_{i}{suf}"
                    if not alt.exists():
                        dst = alt
                        break
                    i += 1
            try:
                shutil.copy2(src, dst)
                copied += 1
            except Exception as e:
                print(f"Failed to copy {src} -> {dst}: {e}")

        QMessageBox.information(self, "Export complete", f"Copied {copied} file(s) to:\n{target}")

    # ---------- Keyboard Shortcuts ----------
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_PageDown):
            self.next_image()
            return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_PageUp):
            self.prev_image()
            return
        if event.key() in (Qt.Key.Key_F, Qt.Key.Key_Space):
            self.toggle_favorite()
            return
        super().keyPressEvent(event)

    def _update_ui_state(self):
        pass


def main():
    import sys
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1100, 800)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

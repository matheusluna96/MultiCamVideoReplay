# replay/main.py
import os, sys, shutil
from PySide6 import QtWidgets
from .config import BUFFER_DIR, EXPORT_DIR, DEFAULT_CAM_INDEXES
from .ui import ReplayWindow
from .widgets import CameraSelectDialog

def main():
    # prepara diretórios
    if os.path.isdir(BUFFER_DIR):
        try: shutil.rmtree(BUFFER_DIR)
        except Exception: pass
    os.makedirs(BUFFER_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    app = QtWidgets.QApplication(sys.argv)

    # seleção inicial de câmeras
    dlg = CameraSelectDialog()
    chosen = None
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        chosen = getattr(dlg, "_res", None)
    if not chosen:
        chosen = tuple(DEFAULT_CAM_INDEXES)

    w = ReplayWindow(chosen)
    w.show()
    app.exec()

if __name__ == "__main__":
    main()

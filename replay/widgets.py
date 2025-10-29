# replay/widgets.py
from typing import List, Optional, Tuple
from PySide6 import QtCore, QtGui, QtWidgets
from .capture import CameraScanWorker

class ImagePane(QtWidgets.QLabel):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 180)
        self.setScaledContents(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:#111; color:#aaa; border:1px solid #333;")
        self._title = title
        self._pix: Optional[QtGui.QPixmap] = None

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        super().paintEvent(e)
        p = QtGui.QPainter(self); r = self.rect()
        if self._pix:
            scaled = self._pix.scaled(r.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation)
            x = (r.width() - scaled.width()) // 2
            y = (r.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            p.setPen(QtGui.QPen(QtGui.QColor("#666")))
            p.drawText(r, QtCore.Qt.AlignmentFlag.AlignCenter, self._title)

    def show_image(self, qimg: Optional[QtGui.QImage]):
        self._pix = QtGui.QPixmap.fromImage(qimg) if qimg else None
        self.update()

class CameraSelectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Câmeras (escolha 2)")
        self.resize(420, 360)
        self.list = QtWidgets.QListWidget()
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.status = QtWidgets.QLabel("Escaneando câmeras...")
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok
                                          | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.list); lay.addWidget(self.status); lay.addWidget(btns)
        self.setStyleSheet("""
            QDialog { background:#0b0b0b; color:#ddd; }
            QListWidget { background:#111; border:1px solid #333; }
            QLabel { color:#ccc; }
        """)
        self.worker = CameraScanWorker()
        self.worker.scanned.connect(self._populate)
        self.worker.start()

    def _populate(self, indices: List[int]):
        self.list.clear()
        for idx in indices:
            it = QtWidgets.QListWidgetItem(f"Câmera {idx}")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, idx)
            self.list.addItem(it)
        self.status.setText("Selecione exatamente 2 e clique em OK." if indices else "Nenhuma câmera encontrada.")

    def get_result(self) -> Optional[Tuple[int,int]]:
        items = self.list.selectedItems()
        if len(items) != 2:
            QtWidgets.QMessageBox.warning(self, "Seleção inválida", "Selecione exatamente 2 câmeras."); return None
        a = items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        b = items[1].data(QtCore.Qt.ItemDataRole.UserRole)
        if a == b:
            QtWidgets.QMessageBox.warning(self, "Seleção inválida", "Escolha duas câmeras diferentes."); return None
        self._res = (a, b); return self._res

    def accept(self):
        if self.get_result() is None: return
        super().accept()

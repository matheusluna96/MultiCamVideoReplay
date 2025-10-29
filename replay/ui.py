# replay/ui.py
import os, time
from typing import Optional, List, Tuple
from PySide6 import QtCore, QtGui, QtWidgets

from .config import (BUFFER_DIR, EXPORT_DIR, BUFFER_SECONDS, WRITE_FPS, PLAYBACK_FPS,
                     JPEG_QUALITY, DEFAULT_CAM_INDEXES)
from .buffer import DiskRingBuffer, cleanup_buffer_dir
from .capture import CaptureWriterThread
from .export import ExportThread
from .widgets import ImagePane, CameraSelectDialog

class ReplayWindow(QtWidgets.QMainWindow):
    def __init__(self, cam_indexes: Tuple[int,int]):
        super().__init__()
        self.setWindowTitle("Vídeo Replay - 2 Câmeras (Buffer JPEG)")
        self.cam_indexes = list(cam_indexes)

        # capacidade do buffer (frames por câmera)
        self.capacity = max(2, int(WRITE_FPS * BUFFER_SECONDS))
        self.ring0 = DiskRingBuffer("0", self.capacity, JPEG_QUALITY)
        self.ring1 = DiskRingBuffer("1", self.capacity, JPEG_QUALITY)

        # threads de captura
        self.th0: Optional[CaptureWriterThread] = None
        self.th1: Optional[CaptureWriterThread] = None
        self._start_writers()

        # estado de reprodução
        self.view_mode = 3       # 1=cam1, 2=cam2, 3=ambas
        self.paused = False
        self.play_ts: Optional[float] = None
        self.last_tick = time.time()
        self.play_speed = 1.0
        self.play_dir = +1

        # UI
        central = QtWidgets.QWidget(self); self.setCentralWidget(central)
        self.p0 = ImagePane("Câmera 1"); self.p1 = ImagePane("Câmera 2")
        self.panesLayout = QtWidgets.QHBoxLayout()
        self.panesLayout.addWidget(self.p0, 1); self.panesLayout.addWidget(self.p1, 1)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, BUFFER_SECONDS * 1000)
        self.slider.setSingleStep(1000 // max(1, int(PLAYBACK_FPS)))
        self.slider.setPageStep(5000)
        self.lbl = QtWidgets.QLabel("00:00:00 / 01:00:00"); self.lbl.setStyleSheet("color:#ccc;")
        self.btn_select = QtWidgets.QPushButton("Selecionar Câmeras")
        self.btn_select.clicked.connect(self._select_cams)
        self.info = QtWidgets.QLabel(self._fmt_info()); self.info.setStyleSheet("color:#8ab4f8;")

        ctrl = QtWidgets.QHBoxLayout()
        ctrl.addWidget(self.lbl); ctrl.addStretch(1); ctrl.addWidget(self.info); ctrl.addSpacing(8); ctrl.addWidget(self.btn_select)

        lay = QtWidgets.QVBoxLayout(central)
        lay.addLayout(self.panesLayout, 1); lay.addWidget(self.slider); lay.addLayout(ctrl)

        self.setStyleSheet("""
            QMainWindow { background:#0b0b0b; }
            QSlider::groove:horizontal { height:6px; background:#333; }
            QSlider::handle:horizontal { background:#999; width:14px; margin:-5px 0; border-radius:6px; }
            QPushButton { background:#1f1f1f; color:#ddd; border:1px solid #444; padding:6px 10px; border-radius:6px; }
            QPushButton:hover { background:#2a2a2a; }
        """)

        # atalhos
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_1), self, activated=self._view_cam1_full)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_2), self, activated=self._view_cam2_full)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_3), self, activated=self._view_both)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Space), self, activated=self._toggle_pause)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Backspace), self, activated=self._jump_now_minus_5)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self, activated=self._step_prev)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self, activated=self._step_next)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Comma), self, activated=self._play_reverse)  # ,
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Period), self, activated=self._play_forward) # .
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Q), self, activated=self._speed_05x)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_W), self, activated=self._speed_1x)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_E), self, activated=self._speed_2x)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Return), self, activated=self._export_triple)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Enter),  self, activated=self._export_triple)

        # slider events
        self._slider_was_paused = None
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.slider.sliderReleased.connect(self._on_slider_released)

        # timer de render
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(1000 / PLAYBACK_FPS))
        self.timer.timeout.connect(self._tick)
        self.timer.start()

        self.resize(1280, 720)
        self._apply_view()
        self._exp_threads: List[ExportThread] = []

    # --- captura ---
    def _start_writers(self):
        # recria diretório do buffer limpo
        if os.path.isdir(BUFFER_DIR):
            try: import shutil; shutil.rmtree(BUFFER_DIR)
            except Exception: pass
        os.makedirs(BUFFER_DIR, exist_ok=True)

        self.ring0 = DiskRingBuffer("0", self.capacity, JPEG_QUALITY)
        self.ring1 = DiskRingBuffer("1", self.capacity, JPEG_QUALITY)
        self._stop_writers()
        self.th0 = CaptureWriterThread(self.cam_indexes[0], self.ring0); self.th0.start()
        self.th1 = CaptureWriterThread(self.cam_indexes[1], self.ring1); self.th1.start()
        self.statusBar().showMessage(f"Iniciadas: camA={self.cam_indexes[0]} camB={self.cam_indexes[1]}", 3000)
        self.play_ts = None

    def _stop_writers(self):
        for th in (self.th0, self.th1):
            if th: th.stop()
        for th in (self.th0, self.th1):
            if th: th.wait(2000)
        self.th0 = None; self.th1 = None

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        self._stop_writers()
        cleanup_buffer_dir()
        return super().closeEvent(e)

    # --- seleção de câmeras ---
    def _fmt_info(self) -> str:
        return f"Câmeras: A={self.cam_indexes[0]}  B={self.cam_indexes[1]}"

    def _select_cams(self):
        dlg = CameraSelectDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            res = getattr(dlg, "_res", None)
            if res:
                a, b = res
                self.cam_indexes = [a, b]
                self.info.setText(self._fmt_info())
                self._start_writers()

    # --- visualização ---
    def _apply_view(self):
        if self.view_mode == 1:
            self.p0.setVisible(True);  self.p1.setVisible(False)
            self.panesLayout.setStretchFactor(self.p0, 1); self.panesLayout.setStretchFactor(self.p1, 0)
        elif self.view_mode == 2:
            self.p0.setVisible(False); self.p1.setVisible(True)
            self.panesLayout.setStretchFactor(self.p0, 0); self.panesLayout.setStretchFactor(self.p1, 1)
        else:
            self.p0.setVisible(True);  self.p1.setVisible(True)
            self.panesLayout.setStretchFactor(self.p0, 1); self.panesLayout.setStretchFactor(self.p1, 1)
        for pane in (self.p0, self.p1):
            pane.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.p0.update(); self.p1.update()

    def _view_cam1_full(self): self.view_mode = 1; self._apply_view()
    def _view_cam2_full(self): self.view_mode = 2; self._apply_view()
    def _view_both(self):      self.view_mode = 3; self._apply_view()

    # --- tempo / slider ---
    def _tails_latest(self) -> Optional[float]:
        t0 = self.ring0.latest_ts(); t1 = self.ring1.latest_ts()
        if t0 is None or t1 is None: return None
        return min(t0, t1)

    def _set_from_slider(self, ms: int):
        latest = self._tails_latest()
        if latest is None: return
        start = latest - BUFFER_SECONDS
        self.play_ts = max(start, min(latest, start + ms/1000.0))

    def _sync_slider(self):
        latest = self._tails_latest()
        if latest is None or self.play_ts is None: return
        start = latest - BUFFER_SECONDS
        pos = int(round((self.play_ts - start) * 1000.0))
        pos = max(0, min(BUFFER_SECONDS*1000, pos))
        b = self.slider.blockSignals(True); self.slider.setValue(pos); self.slider.blockSignals(b)
        rel = max(0.0, min(BUFFER_SECONDS, (self.play_ts - start)))
        hh = int(rel // 3600); mm = int((rel % 3600)//60); ss = int(rel % 60)
        self.lbl.setText(f"{hh:02d}:{mm:02d}:{ss:02d} / 01:00:00")

    def _on_slider_pressed(self):
        if self._slider_was_paused is None:
            self._slider_was_paused = self.paused; self.paused = True

    def _on_slider_changed(self, v: int): self._set_from_slider(v)

    def _on_slider_released(self):
        if self._slider_was_paused is not None:
            self.paused = self._slider_was_paused; self._slider_was_paused = None

    # --- atalhos de controle ---
    def _toggle_pause(self): self.paused = not self.paused

    def _jump_now_minus_5(self):
        latest = self._tails_latest()
        if latest is None: return
        self.play_ts = max(latest - BUFFER_SECONDS, latest - 5.0)

    def _step_prev(self):
        if self.play_ts is None: return
        r0 = self.ring0.step_from(self.play_ts, -1); r1 = self.ring1.step_from(self.play_ts, -1)
        cand = [r for r in (r0, r1) if r]; 
        if not cand: return
        self.play_ts = max(r.ts for r in cand); self.paused = True

    def _step_next(self):
        if self.play_ts is None: return
        r0 = self.ring0.step_from(self.play_ts, +1); r1 = self.ring1.step_from(self.play_ts, +1)
        cand = [r for r in (r0, r1) if r]; 
        if not cand: return
        self.play_ts = min(r.ts for r in cand); self.paused = True

    def _play_reverse(self): self.play_dir = -1; self.paused = False; self.statusBar().showMessage("Reverso", 1200)
    def _play_forward(self): self.play_dir = +1; self.paused = False; self.statusBar().showMessage("Normal", 1200)
    def _speed_05x(self): self.play_speed = 0.5; self.statusBar().showMessage("0.5x", 1200)
    def _speed_1x(self):  self.play_speed = 1.0; self.statusBar().showMessage("1x", 1200)
    def _speed_2x(self):  self.play_speed = 2.0; self.statusBar().showMessage("2x", 1200)

    # --- exportação (Enter → 3 arquivos) ---
    def _export_triple(self):
        latest = self._tails_latest()
        if latest is None or self.play_ts is None:
            QtWidgets.QMessageBox.warning(self, "Exportar clipes", "Buffer insuficiente."); return
        end_ts = min(self.play_ts, latest)
        start_ts = max(end_ts - 20.0, latest - BUFFER_SECONDS)
        if start_ts >= end_ts - (1.0 / PLAYBACK_FPS):
            QtWidgets.QMessageBox.warning(self, "Exportar clipes", "Janela de 20s indisponível."); return

        stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(end_ts))
        MOMENT_DIR = os.path.join(EXPORT_DIR, f"moment_{stamp}")
        os.makedirs(MOMENT_DIR, exist_ok=True)
        paths = [
            (1, os.path.join(MOMENT_DIR, f"clip_cam1_{stamp}.mp4")),
            (2, os.path.join(MOMENT_DIR, f"clip_cam2_{stamp}.mp4")),
            (3, os.path.join(MOMENT_DIR, f"clip_both_{stamp}.mp4")),
        ]
        threads = [ExportThread(self.ring0, self.ring1, start_ts, end_ts, vm, p) for vm, p in paths]
        self._exp_threads = [t for t in self._exp_threads if t.isRunning()] + threads
        for th in threads:
            th.done.connect(self._on_export_done)
            th.error.connect(self._on_export_error)
            th.start()
        self.statusBar().showMessage(f"Exportando 3 clipes (20s): {stamp} ...", 4000)

    def _on_export_done(self, path: str):
        self.statusBar().showMessage(f"Clipe salvo: {os.path.basename(path)}", 4000)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), f"Salvo: {os.path.basename(path)}")

    def _on_export_error(self, msg: str):
        self.statusBar().showMessage("Falha na exportação", 3000)
        QtWidgets.QMessageBox.critical(self, "Exportar clipes", f"Erro: {msg}")

    # --- loop de render ---
    def _tick(self):
        latest = self._tails_latest()
        if latest is None:
            self.p0.show_image(None); self.p1.show_image(None); return
        if self.play_ts is None:
            self.play_ts = max(latest - BUFFER_SECONDS, latest - 5.0)
            self.last_tick = time.time()
        now = time.time(); dt = now - self.last_tick; self.last_tick = now
        if not self.paused:
            start = latest - BUFFER_SECONDS
            self.play_ts = max(start, min(latest, self.play_ts + dt * self.play_speed * self.play_dir))

        ref0 = self.ring0.nearest(self.play_ts); ref1 = self.ring1.nearest(self.play_ts)
        img0 = self.ring0.load_qimage(ref0) if ref0 else None
        img1 = self.ring1.load_qimage(ref1) if ref1 else None
        if self.view_mode == 1:
            self.p0.show_image(img0); self.p1.show_image(None)
        elif self.view_mode == 2:
            self.p0.show_image(None); self.p1.show_image(img1)
        else:
            self.p0.show_image(img0); self.p1.show_image(img1)
        self._sync_slider()

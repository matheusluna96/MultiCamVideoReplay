# replay/capture.py
import time, os
from typing import List
import cv2
from PySide6 import QtCore
from .config import CAPTURE_SIZE, WRITE_FPS, SCAN_RANGE

class CaptureWriterThread(QtCore.QThread):
    """Captura frames e grava no DiskRingBuffer no ritmo WRITE_FPS."""
    def __init__(self, cam_index: int, ring, parent=None):
        super().__init__(parent)
        self.cam_index = cam_index
        self.ring = ring
        self._running = True

    def stop(self): self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_SIZE[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_SIZE[1])
        if not cap.isOpened():
            print(f"[Cam {self.cam_index}] Não abriu.")
            return

        frame_period = 1.0 / WRITE_FPS
        next_write = time.time()

        while self._running:
            ok, frame = cap.read()
            ts = time.time()
            if not ok or frame is None:
                time.sleep(0.01); continue
            if (frame.shape[1], frame.shape[0]) != CAPTURE_SIZE:
                frame = cv2.resize(frame, CAPTURE_SIZE, interpolation=cv2.INTER_AREA)
            if ts >= next_write:
                self.ring.write_frame(frame, ts)
                next_write += frame_period
            time.sleep(0.001)
        cap.release()

class CameraScanWorker(QtCore.QThread):
    scanned = QtCore.Signal(list)  # list[int]
    def run(self):
        found: List[int] = []
        for idx in range(SCAN_RANGE):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            ok = cap.isOpened()
            if ok: ok, _ = cap.read()
            if ok: found.append(idx)
            cap.release()
        self.scanned.emit(found)

# replay/export.py
import os, time
from typing import Optional, Tuple
import numpy as np
import cv2
from PySide6 import QtCore
from .config import EXPORT_DIR, EXPORT_SIZE, PLAYBACK_FPS, FOURCC_MP4, FOURCC_AVI

class ExportThread(QtCore.QThread):
    done = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, ring0, ring1, start_ts: float, end_ts: float, view_mode: int,
                 out_path: str, fps: int = PLAYBACK_FPS, size: Tuple[int,int] = EXPORT_SIZE, parent=None):
        super().__init__(parent)
        self.ring0, self.ring1 = ring0, ring1
        self.start_ts, self.end_ts = start_ts, end_ts
        self.view_mode = view_mode
        self.out_path = out_path
        self.fps = max(1, int(fps))
        self.size = size

    def _compose(self, bgr0, bgr1):
        W, H = self.size
        canvas = np.zeros((H, W, 3), dtype=np.uint8)
        if self.view_mode == 1:
            return cv2.resize(bgr0, (W, H), interpolation=cv2.INTER_AREA) if bgr0 is not None else canvas
        if self.view_mode == 2:
            return cv2.resize(bgr1, (W, H), interpolation=cv2.INTER_AREA) if bgr1 is not None else canvas
        # lado a lado
        lw, rw = W//2, W - W//2
        def fit_center(src, tw, th):
            if src is None: return np.zeros((th, tw, 3), dtype=np.uint8)
            h, w = src.shape[:2]
            s = min(tw/w, th/h); nw, nh = int(w*s), int(h*s)
            resized = cv2.resize(src, (nw, nh), interpolation=cv2.INTER_AREA)
            pad = np.zeros((th, tw, 3), dtype=np.uint8)
            x, y = (tw-nw)//2, (th-nh)//2
            pad[y:y+nh, x:x+nw] = resized
            return pad
        left  = fit_center(bgr0, lw, H)
        right = fit_center(bgr1, rw, H)
        canvas[:, :lw] = left
        canvas[:, lw:] = right
        return canvas

    def _open_writer(self, path):
        fourcc = cv2.VideoWriter_fourcc(*FOURCC_MP4)
        w = cv2.VideoWriter(path, fourcc, self.fps, self.size)
        if w.isOpened(): return w, path
        path2 = os.path.splitext(path)[0] + ".avi"
        fourcc2 = cv2.VideoWriter_fourcc(*FOURCC_AVI)
        w2 = cv2.VideoWriter(path2, fourcc2, self.fps, self.size)
        return (w2, path2) if w2.isOpened() else (None, None)

    def run(self):
        try:
            os.makedirs(EXPORT_DIR, exist_ok=True)
            writer, final_path = self._open_writer(self.out_path)
            if writer is None:
                self.error.emit("VideoWriter não abriu (mp4/avi)."); return
            total = max(1, int(round((self.end_ts - self.start_ts) * self.fps)))
            dt = 1.0 / self.fps; t = self.start_ts
            for i in range(total):
                r0 = self.ring0.nearest(t); r1 = self.ring1.nearest(t)
                b0 = self.ring0.load_bgr(r0) if r0 else None
                b1 = self.ring1.load_bgr(r1) if r1 else None
                frame = self._compose(b0, b1)
                writer.write(frame)
                t = min(self.end_ts, self.start_ts + (i+1)*dt)
            writer.release()
            self.done.emit(final_path)
        except Exception as e:
            self.error.emit(str(e))

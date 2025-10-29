# replay/buffer.py
import os, shutil, threading, time
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import cv2
from PySide6 import QtGui
import atexit

from .config import BUFFER_DIR, JPEG_QUALITY

@dataclass
class DiskFrameRef:
    ts: float
    path: str
    size: Tuple[int, int]  # (w, h)

class DiskRingBuffer:
    """Buffer circular em disco de frames JPEG com índice em memória."""
    def __init__(self, cam_label: str, capacity: int, jpeg_quality: int = JPEG_QUALITY):
        self.root = os.path.join(BUFFER_DIR, f"cam_{cam_label}")
        os.makedirs(self.root, exist_ok=True)
        self.capacity = max(2, int(capacity))
        self.jpeg_quality = int(max(0, min(100, jpeg_quality)))
        self._frames: List[DiskFrameRef] = []
        self._lock = threading.RLock()
        # limpa restos
        for f in os.listdir(self.root):
            p = os.path.join(self.root, f)
            if os.path.isfile(p):
                try: os.remove(p)
                except: pass

    def clear(self):
        with self._lock:
            for ref in self._frames:
                try: os.remove(ref.path)
                except: pass
            self._frames.clear()

    def __len__(self):
        with self._lock: return len(self._frames)

    def latest_ts(self) -> Optional[float]:
        with self._lock:
            return self._frames[-1].ts if self._frames else None

    def oldest_ts(self) -> Optional[float]:
        with self._lock:
            return self._frames[0].ts if self._frames else None

    def write_frame(self, frame_bgr, ts: float):
        fname = f"{int(ts*1e6)}.jpg"
        fpath = os.path.join(self.root, fname)
        try:
            cv2.imwrite(fpath, frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        except Exception:
            return
        h, w = frame_bgr.shape[:2]
        with self._lock:
            self._frames.append(DiskFrameRef(ts=ts, path=fpath, size=(w, h)))
            if len(self._frames) > self.capacity:
                old = self._frames.pop(0)
                try: os.remove(old.path)
                except: pass

    # --- busca binária por timestamp ---
    def _bsearch_ts(self, ts: float) -> int:
        lo, hi = 0, len(self._frames)
        while lo < hi:
            mid = (lo + hi)//2
            if self._frames[mid].ts < ts: lo = mid + 1
            else: hi = mid
        return lo

    def nearest(self, ts: float) -> Optional[DiskFrameRef]:
        with self._lock:
            n = len(self._frames)
            if n == 0: return None
            if ts <= self._frames[0].ts: return self._frames[0]
            if ts >= self._frames[-1].ts: return self._frames[-1]
            i = self._bsearch_ts(ts)
            a, b = self._frames[i-1], self._frames[i]
            return a if abs(a.ts - ts) <= abs(b.ts - ts) else b

    def step_from(self, ts: float, step: int) -> Optional[DiskFrameRef]:
        with self._lock:
            if not self._frames: return None
            i = self._bsearch_ts(ts)
            if i == len(self._frames): i -= 1
            elif i > 0 and abs(self._frames[i].ts - ts) > abs(self._frames[i-1].ts - ts):
                i -= 1
            ni = max(0, min(len(self._frames)-1, i + step))
            return self._frames[ni]

    # --- carregadores ---
    def load_qimage(self, ref: DiskFrameRef) -> Optional[QtGui.QImage]:
        if ref is None or not os.path.exists(ref.path): return None
        try:
            buf = np.fromfile(ref.path, dtype=np.uint8)
            bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception:
            bgr = cv2.imread(ref.path, cv2.IMREAD_COLOR)
        if bgr is None: return None
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QtGui.QImage(rgb.data, w, h, w*3, QtGui.QImage.Format.Format_RGB888)
        return qimg.copy()

    def load_bgr(self, ref: DiskFrameRef):
        if ref is None or not os.path.exists(ref.path): return None
        try:
            buf = np.fromfile(ref.path, dtype=np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception:
            return cv2.imread(ref.path, cv2.IMREAD_COLOR)

# --- limpeza do diretório inteiro ---
def cleanup_buffer_dir():
    try:
        if os.path.isdir(BUFFER_DIR):
            shutil.rmtree(BUFFER_DIR, ignore_errors=False)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[CLEANUP] Falha ao remover '{BUFFER_DIR}': {e}")

atexit.register(cleanup_buffer_dir)

# replay/config.py
import os

# --- captura / buffer ---
BUFFER_SECONDS = 60 * 60          # 1 hora
WRITE_FPS = 20                    # gravação do buffer (por câmera)
PLAYBACK_FPS = 30                 # FPS da UI e exportação
JPEG_QUALITY = 80                 # 0..100
CAPTURE_SIZE = (1920, 1080)       # 1080p
DEFAULT_CAM_INDEXES = [0, 1]
SCAN_RANGE = 11                   # varrer 0..10

# --- paths ---
ROOT = os.path.abspath(os.path.dirname(__file__))
BUFFER_DIR = os.path.join(ROOT, "buffer_jpeg")
EXPORT_DIR = os.path.join(ROOT, "exports")

# --- exportação ---
EXPORT_SIZE = (1920, 1080)
FOURCC_MP4 = "mp4v"               # tenta MP4
FOURCC_AVI = "MJPG"               # fallback AVI

#!/usr/bin/env python3
"""
Configuración compartida: vídeo, GPS, UDP imágenes, recordings por sesión, límites.
Valores desde variables de entorno con defaults seguros para desarrollo.
"""

import os
import struct

_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_BASE)
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "datos_vuelo")

# ===== RECORDINGS (raíz del repo) =====
_recordings_override = os.environ.get("RECORDINGS_DIR", "").strip()
RECORDINGS_DIR = _recordings_override or os.path.join(PROJECT_ROOT, "recordings")
ANALYSIS_SUBDIR = os.environ.get("ANALYSIS_SUBDIR", "analysis")
VIDEO_SOURCE_SUBDIR = os.environ.get("VIDEO_SOURCE_SUBDIR", "video_source")
SESSION_ID_MAX_LEN = 31

# ===== VIDEO / IMAGEN =====
_cam_str = os.environ.get("CAMERA_INDICES", "0,1,2")
CAMERA_INDICES = [int(x.strip()) for x in _cam_str.split(",") if x.strip()]
FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", "640"))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", "360"))
FPS = int(os.environ.get("FPS", "15"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "92"))
JPEG_LUMA_QUALITY = int(os.environ.get("JPEG_LUMA_QUALITY", "24"))
JPEG_CHROMA_QUALITY = int(os.environ.get("JPEG_CHROMA_QUALITY", "30"))
ROTATE = int(os.environ.get("ROTATE", "0"))
MAX_QUEUE_SIZE = int(os.environ.get("MAX_QUEUE_SIZE", "300"))
# 1 = pedir MJPEG al driver USB (no es grabación a archivo); 0 = formato por defecto (p. ej. YUYV)
CAMERA_USE_MJPEG = os.environ.get("CAMERA_USE_MJPEG", "1") == "1"

# Perfiles rápidos (opcional; solo uno activo)
if os.environ.get("IMG_UDP_QUALITY_MAX", "0") == "1":
	FRAME_WIDTH, FRAME_HEIGHT, FPS, JPEG_QUALITY = 1920, 1080, 60, 95
elif os.environ.get("IMG_UDP_QUALITY_SUPERIOR", "0") == "1":
	FRAME_WIDTH, FRAME_HEIGHT, FPS, JPEG_QUALITY = 1280, 720, 60, 90

# Captura orientada a análisis en disco (Orange Pi): sube calidad JPEG respecto al perfil anterior
if os.environ.get("ORANGE_ANALYSIS_MAX", "0") == "1":
	JPEG_QUALITY = int(os.environ.get("ANALYSIS_JPEG_QUALITY", "98"))

# ===== GPS =====
GPS_PORT = os.environ.get("GPS_PORT", "/dev/ttyS3")
GPS_BAUDRATE = int(os.environ.get("GPS_BAUD", os.environ.get("GPS_BAUDRATE", "9600")))
GPS_TIMEOUT = float(os.environ.get("GPS_TIMEOUT", "1"))

# ===== UDP (imágenes fragmentadas) =====
UDP_BIND_HOST = os.environ.get("UDP_BIND_HOST", "0.0.0.0")
UDP_PORT = int(os.environ.get("UDP_PORT", "5555"))
UDP_DEST_IP = (
	os.environ.get("UDP_DEST_IP", "").strip()
	or os.environ.get("UDP_HOST", "").strip()
)
UDP_PACKET_SIZE = int(os.environ.get("UDP_PACKET_SIZE", "1400"))
UDP_RETRANSMIT = int(os.environ.get("UDP_RETRANSMIT", "0"))

# Cola emisor Pi: desacoplar envío UDP (y disco) del ritmo de captura
IMG_UDP_SEND_QUEUE_SIZE = max(1, int(os.environ.get("IMG_UDP_SEND_QUEUE_SIZE", "4")))
IMG_UDP_QUEUE_DROP_OLDEST = os.environ.get("IMG_UDP_QUEUE_DROP_OLDEST", "1") == "1"
DISK_SAVE_QUEUE_SIZE = max(1, int(os.environ.get("DISK_SAVE_QUEUE_SIZE", "8")))
SAVE_LOCAL_EVERY_N = max(1, int(os.environ.get("SAVE_LOCAL_EVERY_N", "1")))

# Cabecera: seq(I) total(H) idx(H) session(32s) ts(d) lat(d) lon(d) alt(f) qual(B)
IMG_UDP_SESSION_BYTES = 32
IMG_UDP_HEADER_FORMAT = "!I H H 32s d d d f B"
IMG_UDP_HEADER_SIZE = struct.calcsize(IMG_UDP_HEADER_FORMAT)

# ===== GUARDADO =====
SAVE_LOCAL_ANALYSIS = os.environ.get("SAVE_LOCAL_ANALYSIS", os.environ.get("SAVE_LOCAL_IMAGES", "1")) == "1"
SAVE_LOCAL_IMAGES = SAVE_LOCAL_ANALYSIS
IMAGE_SAVE_DIR = os.path.join(DATA_DIR, "imagenes")

SAVE_HOST_FRAMES = os.environ.get("SAVE_HOST_FRAMES", "1") == "1"
HOST_SAVE_JPEG_QUALITY = int(os.environ.get("HOST_SAVE_JPEG_QUALITY", "75"))

# ===== LÍMITES (telemetría / ResourceLimiter) =====
MAX_CPU_PERCENT = int(os.environ.get("MAX_CPU_PERCENT", "70"))
MAX_MEMORY_PERCENT = int(os.environ.get("MAX_MEMORY_PERCENT", "80"))


def pack_session_id(session_id: str) -> bytes:
	"""ASCII/UTF-8 truncado a SESSION_ID_MAX_LEN, relleno a 32 bytes."""
	raw = session_id.encode("utf-8", errors="replace")[:SESSION_ID_MAX_LEN]
	if len(raw) > IMG_UDP_SESSION_BYTES:
		raw = raw[:IMG_UDP_SESSION_BYTES]
	return raw.ljust(IMG_UDP_SESSION_BYTES, b"\x00")


def unpack_session_id(raw: bytes) -> str:
	return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def ensure_data_dirs():
	"""Legado: stream/datos_vuelo (opcional). Las sesiones usan RECORDINGS_DIR."""
	os.makedirs(DATA_DIR, exist_ok=True)
	if SAVE_LOCAL_ANALYSIS:
		os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

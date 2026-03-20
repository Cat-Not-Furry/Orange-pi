#!/usr/bin/env python3
"""
Configuración centralizada para el cliente TCP de Orange Pi.
Variables desde entorno; modos de calidad predefinidos.
"""

import os

# Conexión TCP
TCP_HOST = os.environ.get("TCP_HOST", "")
TCP_PORT = int(os.environ.get("TCP_PORT", "5555"))
GPS_PORT = os.environ.get("GPS_PORT", "/dev/ttyS3")
GPS_BAUD = int(os.environ.get("GPS_BAUD", "9600"))

# Modos de calidad (solo uno activo a la vez)
TCP_QUALITY_MAX = os.environ.get("TCP_QUALITY_MAX", "0") == "1"
TCP_QUALITY_SUPERIOR = os.environ.get("TCP_QUALITY_SUPERIOR", "0") == "1"
TCP_QUALITY_NORMAL = os.environ.get("TCP_QUALITY_NORMAL", "0") == "1"

# Parámetros por modo: (width, height, fps, jpeg_quality)
MODE_MAX = (1920, 1080, 60, 95)
MODE_SUPERIOR = (1280, 720, 60, 90)
MODE_NORMAL = (640, 360, 30, 70)


def get_video_params():
	"""Devuelve (width, height, fps, jpeg_quality) según modo activo."""
	if TCP_QUALITY_MAX:
		return MODE_MAX
	if TCP_QUALITY_SUPERIOR:
		return MODE_SUPERIOR
	if TCP_QUALITY_NORMAL:
		return MODE_NORMAL
	return MODE_NORMAL


# Cámara (índices a probar: /dev/video0, video1, video2...)
_cam_str = os.environ.get("CAMERA_INDICES", "0,1,2")
CAMERA_INDICES = [int(x.strip()) for x in _cam_str.split(",") if x.strip()]

# Datos de vuelo (Orange Pi)
DATOS_VUELO_DIR = os.path.join(os.path.dirname(__file__), "datos_vuelo")
SEGMENT_DURATION_SEC = 60

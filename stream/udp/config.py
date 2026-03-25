#!/usr/bin/env python3
"""
Configuración del cliente UDP (Orange Pi). Destino = laptop (UDP_HOST).
"""

import os

# Destino en laptop
UDP_HOST = os.environ.get("UDP_HOST", "")
UDP_PORT = int(os.environ.get("UDP_PORT", "5555"))
UDP_PACKET_SIZE = int(os.environ.get("UDP_PACKET_SIZE", "1400"))

GPS_PORT = os.environ.get("GPS_PORT", "/dev/ttyS3")
GPS_BAUD = int(os.environ.get("GPS_BAUD", "9600"))

UDP_QUALITY_MAX = os.environ.get("UDP_QUALITY_MAX", "0") == "1"
UDP_QUALITY_SUPERIOR = os.environ.get("UDP_QUALITY_SUPERIOR", "0") == "1"
UDP_QUALITY_NORMAL = os.environ.get("UDP_QUALITY_NORMAL", "0") == "1"

MODE_MAX = (1920, 1080, 60, 95)
MODE_SUPERIOR = (1280, 720, 60, 90)
MODE_NORMAL = (640, 360, 30, 70)


def get_video_params():
	"""Devuelve (width, height, fps, jpeg_quality) según modo activo."""
	if UDP_QUALITY_MAX:
		return MODE_MAX
	if UDP_QUALITY_SUPERIOR:
		return MODE_SUPERIOR
	if UDP_QUALITY_NORMAL:
		return MODE_NORMAL
	return MODE_NORMAL


_cam_str = os.environ.get("CAMERA_INDICES", "0,1,2")
CAMERA_INDICES = [int(x.strip()) for x in _cam_str.split(",") if x.strip()]

DATOS_VUELO_DIR = os.path.join(os.path.dirname(__file__), "datos_vuelo")

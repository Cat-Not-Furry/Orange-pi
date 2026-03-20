#!/usr/bin/env python3
"""
Guardado local en Orange Pi: video en segmentos, GPS en CSV.
"""

import csv
import logging
import os
import threading
import time
from datetime import datetime

import cv2

from . import config

logger = logging.getLogger(__name__)


class DataLogger:
	"""Guarda video en segmentos y GPS en CSV. Thread-safe."""

	def __init__(self, width: int, height: int, fps: float = 30):
		self.width = width
		self.height = height
		self.fps = fps
		self._dir = config.DATOS_VUELO_DIR
		self._segment_duration = config.SEGMENT_DURATION_SEC
		self._lock = threading.Lock()
		self._writer = None
		self._out_path = None
		self._segment_start = None
		self._csv_file = None
		self._csv_writer = None

	def _ensure_dir(self):
		os.makedirs(self._dir, exist_ok=True)

	def _start_segment(self):
		"""Inicia nuevo segmento de video."""
		self._ensure_dir()
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		base = os.path.join(self._dir, f"video_{timestamp}")
		codecs = [("avc1", ".mp4"), ("H264", ".mp4"), ("mp4v", ".mp4"), ("MJPG", ".avi")]
		for fourcc_str, ext in codecs:
			out_path = base + ext
			fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
			writer = cv2.VideoWriter(out_path, fourcc, self.fps, (self.width, self.height))
			if writer.isOpened():
				self._writer = writer
				self._out_path = out_path
				self._segment_start = time.time()
				logger.info(f"Segmento iniciado: {out_path}")
				return
			writer.release()
		logger.warning("No se pudo crear VideoWriter para segmento")

	def _maybe_rotate_segment(self):
		if self._segment_start and (time.time() - self._segment_start) >= self._segment_duration:
			if self._writer and self._writer.isOpened():
				self._writer.release()
				self._writer = None
			self._segment_start = None
			self._start_segment()

	def write_frame(self, frame):
		"""Escribe un frame (numpy array BGR)."""
		with self._lock:
			self._maybe_rotate_segment()
			if self._writer is None:
				self._start_segment()
			if self._writer and self._writer.isOpened() and frame is not None:
				h, w = frame.shape[:2]
				if (w, h) == (self.width, self.height):
					self._writer.write(frame)
				elif w > 0 and h > 0:
					resized = cv2.resize(frame, (self.width, self.height))
					self._writer.write(resized)

	def log_gps(self, lat: float, lon: float, alt: float, timestamp: float = None):
		"""Añade punto GPS al CSV."""
		with self._lock:
			self._ensure_dir()
			csv_path = os.path.join(self._dir, "gps_backup.csv")
			ts = datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()
			write_header = not os.path.isfile(csv_path) or os.path.getsize(csv_path) == 0
			try:
				with open(csv_path, "a", newline="") as f:
					w = csv.writer(f)
					if write_header:
						w.writerow(["timestamp", "lat", "lon", "alt"])
					w.writerow([ts, lat, lon, alt])
			except Exception as e:
				logger.warning(f"Error escribiendo GPS: {e}")

	def close(self):
		"""Cierra writer y archivos."""
		with self._lock:
			if self._writer and self._writer.isOpened():
				self._writer.release()
				self._writer = None
			self._segment_start = None

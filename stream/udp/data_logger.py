#!/usr/bin/env python3
"""
Backup local de GPS en Orange Pi (modo UDP). Misma política que stream.tcp.data_logger.
"""

import csv
import logging
import os
import threading
from datetime import datetime

from . import config

logger = logging.getLogger(__name__)


class DataLogger:
	"""Solo backup GPS en CSV bajo stream/udp/datos_vuelo/."""

	def __init__(self, width: int = 0, height: int = 0, fps: float = 30):
		self._dir = config.DATOS_VUELO_DIR
		self._lock = threading.Lock()

	def _ensure_dir(self):
		os.makedirs(self._dir, exist_ok=True)

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
				logger.warning("Error escribiendo GPS: %s", e)

	def close(self):
		pass

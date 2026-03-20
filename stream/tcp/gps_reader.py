#!/usr/bin/env python3
"""
Lector de GPS por puerto serie. Hilo que mantiene el último dato válido.
"""

import logging
import threading
import time

try:
	import serial
	import pynmea2
except ImportError:
	serial = None
	pynmea2 = None

logger = logging.getLogger(__name__)


class GPSReader:
	"""Hilo que lee NMEA del puerto serie y mantiene último dato con lock."""

	def __init__(self, port: str, baud: int = 9600):
		self.port = port
		self.baud = baud
		self._last_data = None
		self._lock = threading.Lock()
		self._stop = threading.Event()
		self._thread = None
		self._ser = None

	def get_data(self):
		"""Devuelve último dato: dict con lat, lon, alt, quality, satellites o None."""
		with self._lock:
			return self._last_data

	def _run(self):
		if not serial or not pynmea2:
			logger.warning("pyserial o pynmea2 no instalados. GPS inactivo.")
			return
		while not self._stop.is_set():
			try:
				self._ser = serial.Serial(self.port, self.baud, timeout=1)
				logger.info(f"GPS conectado en {self.port}")
				while not self._stop.is_set():
					line = self._ser.readline().decode("ascii", errors="ignore").strip()
					if not line or not line.startswith("$"):
						continue
					try:
						msg = pynmea2.parse(line)
						if hasattr(msg, "latitude") and hasattr(msg, "longitude"):
							lat = msg.latitude if msg.latitude else 0.0
							lon = msg.longitude if msg.longitude else 0.0
							alt = getattr(msg, "altitude", None) or 0.0
							quality = getattr(msg, "gps_qual", 0) or 0
							satellites = getattr(msg, "num_sats", 0) or 0
							with self._lock:
								self._last_data = {
									"lat": lat,
									"lon": lon,
									"alt": float(alt) if alt else 0.0,
									"quality": int(quality),
									"satellites": int(satellites),
								}
					except pynmea2.ParseError:
						pass
			except Exception as e:
				logger.warning(f"GPS error: {e}")
			finally:
				if self._ser and self._ser.is_open:
					try:
						self._ser.close()
					except Exception:
						pass
					self._ser = None
			if not self._stop.is_set():
				time.sleep(5)

	def start(self):
		"""Inicia el hilo de lectura."""
		self._stop.clear()
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()

	def stop(self):
		"""Detiene el hilo."""
		self._stop.set()
		if self._ser and self._ser.is_open:
			try:
				self._ser.close()
			except Exception:
				pass

#!/usr/bin/env python3
"""
Cliente TCP que envía paquetes de video+GPS al receptor en laptop.
Formato: [4B: len_jpeg][8B: timestamp][8B: lat][8B: lon][4B: alt][1B: quality][2B: satellites][jpeg]
"""

import logging
import socket
import struct
import threading
import time

logger = logging.getLogger(__name__)

# [8B timestamp][8B lat][8B lon][4B alt][1B quality][2B satellites]
META_FORMAT = ">dddfBH"
META_SIZE = struct.calcsize(META_FORMAT)


def pack_packet(jpeg_bytes: bytes, timestamp: float, lat: float, lon: float, alt: float, quality: int, satellites: int) -> bytes:
	"""Empaqueta frame JPEG con metadatos."""
	jpeg_len = len(jpeg_bytes)
	header = struct.pack(">I", jpeg_len)
	meta = struct.pack(META_FORMAT, timestamp, lat, lon, alt, quality, satellites)
	return header + meta + jpeg_bytes


class TCPSender:
	"""Cliente TCP que envía paquetes. Reintenta cada 5s si falla."""

	def __init__(self, host: str, port: int, put_back_callback=None):
		self.host = host
		self.port = port
		self._put_back_callback = put_back_callback
		self._sock = None
		self._stop = threading.Event()
		self._connected = False

	def _connect(self) -> bool:
		try:
			if self._sock:
				try:
					self._sock.close()
				except Exception:
					pass
				self._sock = None
			self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._sock.settimeout(10)
			self._sock.connect((self.host, self.port))
			self._sock.settimeout(None)
			self._connected = True
			logger.info(f"Conectado a {self.host}:{self.port}")
			return True
		except Exception as e:
			logger.warning(f"Conexión fallida: {e}")
			self._connected = False
			return False

	def send(self, jpeg_bytes: bytes, timestamp: float, lat: float, lon: float, alt: float, quality: int, satellites: int) -> bool:
		"""Envía un paquete. Si falla, devuelve False (el caller puede reencolar)."""
		if not self._connected or not self._sock:
			if not self._connect():
				return False
		try:
			data = pack_packet(jpeg_bytes, timestamp, lat, lon, alt, quality, satellites)
			self._sock.sendall(data)
			return True
		except Exception as e:
			logger.warning(f"Envío fallido: {e}")
			self._connected = False
			if self._sock:
				try:
					self._sock.close()
				except Exception:
					pass
				self._sock = None
			return False

	def close(self):
		"""Cierra la conexión."""
		self._stop.set()
		if self._sock:
			try:
				self._sock.close()
			except Exception:
				pass
			self._sock = None
		self._connected = False

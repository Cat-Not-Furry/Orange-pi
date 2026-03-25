#!/usr/bin/env python3
"""
Envío UDP de frames JPEG fragmentados. Cabecera fija por datagrama + payload.
"""

import logging
import socket
import struct
import threading

logger = logging.getLogger(__name__)

# seq(I) frag_count(H) frag_idx(H) ts(d) lat(d) lon(d) alt(f) quality(B) satellites(H)
UDP_HEADER_FORMAT = ">IHHdddfBH"
UDP_HEADER_SIZE = struct.calcsize(UDP_HEADER_FORMAT)


def pack_udp_header(seq, frag_count, frag_idx, timestamp, lat, lon, alt, quality, satellites):
	return struct.pack(
		UDP_HEADER_FORMAT,
		seq & 0xFFFFFFFF,
		frag_count,
		frag_idx,
		float(timestamp),
		float(lat),
		float(lon),
		float(alt),
		int(quality) & 0xFF,
		int(satellites) & 0xFFFF,
	)


class UDPSender:
	"""Envía JPEG fragmentado por UDP."""

	def __init__(self, host: str, port: int, packet_size: int = 1400):
		if not host:
			raise ValueError("UDP_HOST vacío: indica la IP de la laptop")
		self.host = host
		self.port = port
		self.packet_size = max(512, int(packet_size))
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._seq = 0
		self._lock = threading.Lock()

	def send_frame(self, jpeg_bytes: bytes, timestamp: float, lat: float, lon: float, alt: float, quality: int, satellites: int):
		"""Fragmenta y envía un frame completo."""
		max_payload = self.packet_size - UDP_HEADER_SIZE
		if max_payload <= 0:
			logger.error("UDP_PACKET_SIZE demasiado pequeña")
			return
		n = len(jpeg_bytes)
		frag_count = (n + max_payload - 1) // max_payload
		if frag_count > 65535:
			logger.warning("JPEG demasiado grande para UDP; omitiendo frame")
			return
		with self._lock:
			seq = self._seq
			self._seq = (self._seq + 1) & 0xFFFFFFFF
		for frag_idx in range(frag_count):
			start = frag_idx * max_payload
			end = min(start + max_payload, n)
			payload = jpeg_bytes[start:end]
			hdr = pack_udp_header(seq, frag_count, frag_idx, timestamp, lat, lon, alt, quality, satellites)
			try:
				self._sock.sendto(hdr + payload, (self.host, self.port))
			except OSError as e:
				logger.warning("UDP sendto error: %s", e)

	def close(self):
		try:
			self._sock.close()
		except Exception:
			pass

#!/usr/bin/env python3
"""
Envío de frames MJPEG por UDP con fragmentación.
Protocolo: frame_id (4B) + chunk_idx (2B) + total_chunks (2B) + payload
"""

import os
import socket
import struct
import threading
import time
import logging

logger = logging.getLogger(__name__)

CHUNK_MAX = 1400  # Por debajo de MTU 1472
HEADER_SIZE = 8


def fragment_frame(frame_bytes: bytes, frame_id: int) -> list[bytes]:
	"""Divide un frame en chunks con cabecera."""
	payload_size = CHUNK_MAX - HEADER_SIZE
	total = (len(frame_bytes) + payload_size - 1) // payload_size
	chunks = []
	for idx in range(total):
		offset = idx * payload_size
		chunk_data = frame_bytes[offset : offset + payload_size]
		header = struct.pack(">IHH", frame_id, idx, total)
		chunks.append(header + chunk_data)
	return chunks


class UDPSender:
	"""Envía frames JPEG fragmentados por UDP."""

	def __init__(self, target_ip: str, target_port: int):
		self.target = (target_ip, target_port)
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._frame_id = 0
		self._lock = threading.Lock()

	def send_frame(self, frame_bytes: bytes) -> int:
		"""Envía un frame fragmentado. Retorna número de bytes enviados."""
		with self._lock:
			fid = self._frame_id
			self._frame_id = (self._frame_id + 1) & 0xFFFFFFFF
		chunks = fragment_frame(frame_bytes, fid)
		total_sent = 0
		for chunk in chunks:
			try:
				self._sock.sendto(chunk, self.target)
				total_sent += len(chunk)
			except OSError as e:
				logger.warning(f"UDP send error: {e}")
				break
		return total_sent

	def close(self) -> None:
		self._sock.close()


def udp_send_loop(frame_getter, target_ip: str, target_port: int, fps: float) -> None:
	"""
	Hilo que obtiene frames de frame_getter() y los envía por UDP.
	frame_getter debe retornar bytes o None.
	"""
	sender = UDPSender(target_ip, target_port)
	interval = 1.0 / fps if fps > 0 else 0.033
	next_send = time.perf_counter()
	while True:
		frame_bytes = frame_getter()
		if frame_bytes:
			sender.send_frame(frame_bytes)
		next_send += interval
		now = time.perf_counter()
		if next_send < now:
			next_send = now + interval
		time.sleep(max(0, next_send - now))

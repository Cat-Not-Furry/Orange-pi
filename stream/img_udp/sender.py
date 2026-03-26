#!/usr/bin/env python3
"""
Emisor Orange Pi: JPEG fragmentado por UDP con metadatos GPS y session_id por datagrama.
"""

import logging
import os
import socket
import struct
import threading
import time
from datetime import datetime

from stream.common import config
from stream.common.gps_reader import GPSReader
from stream.common.video_capture import VideoCapture

logger = logging.getLogger(__name__)


class UDPImageSender(threading.Thread):
	def __init__(self, session_id: str):
		super().__init__(daemon=True)
		sid = (session_id or "").strip()
		if not sid:
			raise ValueError("session_id vacío")
		self.session_id = sid
		self._session_bytes = config.pack_session_id(sid)
		self._analysis_dir = os.path.join(
			config.RECORDINGS_DIR,
			self.session_id,
			config.ANALYSIS_SUBDIR,
		)
		if config.SAVE_LOCAL_ANALYSIS:
			os.makedirs(self._analysis_dir, exist_ok=True)
		self.video = VideoCapture()
		self.gps = GPSReader(config.GPS_PORT, config.GPS_BAUDRATE)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.running = True
		self.seq = 0
		self.stats = {"sent": 0}
		if not config.UDP_DEST_IP:
			raise ValueError(
				"Define UDP_DEST_IP o UDP_HOST con la IP de la laptop. "
				"Ej: UDP_DEST_IP=192.168.1.50 python -m stream.img_udp.main"
			)
		self._dest = (config.UDP_DEST_IP, config.UDP_PORT)

	def run(self):
		self.video.start()
		self.gps.start()

		logger.info(
			"Sesión %s | Emisor UDP | %sx%s @ %s fps | JPEG %s → %s:%s | análisis local: %s",
			self.session_id,
			config.FRAME_WIDTH,
			config.FRAME_HEIGHT,
			config.FPS,
			config.JPEG_QUALITY,
			config.UDP_DEST_IP,
			config.UDP_PORT,
			self._analysis_dir if config.SAVE_LOCAL_ANALYSIS else "(desactivado)",
		)

		while self.running:
			frame_data = self.video.get_frame(timeout=1.0)
			if frame_data is None:
				continue
			jpeg_bytes, ts, _fn = frame_data
			gps = self.gps.get_data() or {}
			self._send_fragmented(jpeg_bytes, gps, ts)

			if config.SAVE_LOCAL_ANALYSIS:
				self._save_local(jpeg_bytes, gps)

			self.seq = (self.seq + 1) & 0xFFFFFFFF

		self.video.stop()
		self.gps.stop()
		self.video.join(timeout=3.0)
		self.gps.join(timeout=2.0)
		self.sock.close()

	def _send_fragmented(self, img_data, gps, timestamp):
		header_size = config.IMG_UDP_HEADER_SIZE
		max_payload = config.UDP_PACKET_SIZE - header_size
		if max_payload <= 0:
			raise ValueError("UDP_PACKET_SIZE demasiado pequeña para la cabecera")

		total = (len(img_data) + max_payload - 1) // max_payload
		if total > 65535:
			logger.warning("JPEG demasiado grande (%s bytes); omitiendo frame", len(img_data))
			return

		lat = float(gps.get("lat", 0.0))
		lon = float(gps.get("lon", 0.0))
		alt = float(gps.get("alt", 0.0))
		qual = int(gps.get("quality", 0)) & 0xFF
		repeat = max(1, config.UDP_RETRANSMIT)

		for i in range(total):
			start = i * max_payload
			end = min(start + max_payload, len(img_data))
			payload = img_data[start:end]
			packet = struct.pack(
				config.IMG_UDP_HEADER_FORMAT,
				self.seq & 0xFFFFFFFF,
				total,
				i,
				self._session_bytes,
				float(timestamp),
				lat,
				lon,
				alt,
				qual,
			) + payload

			for _ in range(repeat):
				try:
					self.sock.sendto(packet, self._dest)
				except OSError as e:
					logger.warning("sendto: %s", e)
				if repeat > 1:
					time.sleep(0.0005)

		self.stats["sent"] += total * repeat

	def _save_local(self, img_data, gps):
		filename = datetime.now().strftime("img_%Y%m%d_%H%M%S_%f.jpg")
		path = os.path.join(self._analysis_dir, filename)
		with open(path, "wb") as f:
			f.write(img_data)
		meta_path = path.replace(".jpg", ".gps")
		line = "{},{},{},{},{}\n".format(
			gps.get("timestamp", ""),
			gps.get("lat", ""),
			gps.get("lon", ""),
			gps.get("alt", ""),
			gps.get("quality", ""),
		)
		with open(meta_path, "w", encoding="utf-8") as f:
			f.write(line)

	def stop(self):
		self.running = False

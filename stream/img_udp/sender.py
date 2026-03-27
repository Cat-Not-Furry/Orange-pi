#!/usr/bin/env python3
"""
Emisor Orange Pi: JPEG fragmentado por UDP con metadatos GPS y session_id por datagrama.
Envío y guardado local en colas con hilos worker para no bloquear la captura.
"""

import logging
import os
import queue
import socket
import struct
import threading
import time
from datetime import datetime

from stream.common import config
from stream.common.gps_reader import GPSReader
from stream.common.video_capture import VideoCapture

logger = logging.getLogger(__name__)

_NET_STOP = object()
_DISK_STOP = object()


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
		self._seq_lock = threading.Lock()
		self.stats = {"sent": 0, "dropped_net_queue": 0, "dropped_disk_queue": 0}
		self._save_counter = 0
		self._net_queue = queue.Queue(maxsize=config.IMG_UDP_SEND_QUEUE_SIZE)
		self._disk_queue = (
			queue.Queue(maxsize=config.DISK_SAVE_QUEUE_SIZE)
			if config.SAVE_LOCAL_ANALYSIS
			else None
		)
		self._net_thread = None
		self._disk_thread = None
		if not config.UDP_DEST_IP:
			raise ValueError(
				"Define UDP_DEST_IP o UDP_HOST con la IP de la laptop. "
				"Ej: UDP_DEST_IP=192.168.1.50 python -m stream.img_udp.main"
			)
		self._dest = (config.UDP_DEST_IP, config.UDP_PORT)

	def _enqueue_net(self, seq: int, jpeg_bytes: bytes, gps: dict, ts: float) -> None:
		item = (seq, jpeg_bytes, gps, ts)
		q = self._net_queue
		if config.IMG_UDP_QUEUE_DROP_OLDEST:
			while q.full():
				try:
					q.get_nowait()
					self.stats["dropped_net_queue"] += 1
				except queue.Empty:
					break
		try:
			q.put_nowait(item)
		except queue.Full:
			self.stats["dropped_net_queue"] += 1

	def _enqueue_disk(self, jpeg_bytes: bytes, gps: dict) -> None:
		if self._disk_queue is None:
			return
		item = (jpeg_bytes, gps)
		q = self._disk_queue
		if config.IMG_UDP_QUEUE_DROP_OLDEST:
			while q.full():
				try:
					q.get_nowait()
					self.stats["dropped_disk_queue"] += 1
				except queue.Empty:
					break
		try:
			q.put_nowait(item)
		except queue.Full:
			self.stats["dropped_disk_queue"] += 1

	def _net_worker(self) -> None:
		while True:
			try:
				item = self._net_queue.get(timeout=0.5)
			except queue.Empty:
				if not self.running and self._net_queue.empty():
					continue
				continue
			if item is _NET_STOP:
				break
			seq, jpeg_bytes, gps, ts = item
			self._send_fragmented(jpeg_bytes, gps, ts, seq)

	def _disk_worker(self) -> None:
		if self._disk_queue is None:
			return
		while True:
			try:
				item = self._disk_queue.get(timeout=0.5)
			except queue.Empty:
				if not self.running and self._disk_queue.empty():
					continue
				continue
			if item is _DISK_STOP:
				break
			jpeg_bytes, gps = item
			self._save_local(jpeg_bytes, gps)

	def run(self):
		self._net_thread = threading.Thread(target=self._net_worker, daemon=True)
		self._net_thread.start()
		if config.SAVE_LOCAL_ANALYSIS and self._disk_queue is not None:
			self._disk_thread = threading.Thread(target=self._disk_worker, daemon=True)
			self._disk_thread.start()

		self.video.start()
		self.gps.start()

		logger.info(
			"Sesión %s | Emisor UDP | %sx%s @ %s fps | JPEG %s → %s:%s | análisis: %s | cola UDP %s (drop_oldest=%s)",
			self.session_id,
			config.FRAME_WIDTH,
			config.FRAME_HEIGHT,
			config.FPS,
			config.JPEG_QUALITY,
			config.UDP_DEST_IP,
			config.UDP_PORT,
			self._analysis_dir if config.SAVE_LOCAL_ANALYSIS else "(desactivado)",
			config.IMG_UDP_SEND_QUEUE_SIZE,
			config.IMG_UDP_QUEUE_DROP_OLDEST,
		)

		while self.running:
			frame_data = self.video.get_frame(timeout=1.0)
			if frame_data is None:
				continue
			jpeg_bytes, ts, _fn = frame_data
			gps = self.gps.get_data() or {}

			with self._seq_lock:
				use_seq = self.seq
				self.seq = (self.seq + 1) & 0xFFFFFFFF

			self._enqueue_net(use_seq, jpeg_bytes, gps, ts)

			if config.SAVE_LOCAL_ANALYSIS:
				self._save_counter += 1
				if self._save_counter % config.SAVE_LOCAL_EVERY_N == 0:
					gps_copy = dict(gps)
					self._enqueue_disk(jpeg_bytes, gps_copy)

		try:
			self._net_queue.put_nowait(_NET_STOP)
		except queue.Full:
			try:
				self._net_queue.get_nowait()
			except queue.Empty:
				pass
			self._net_queue.put_nowait(_NET_STOP)

		if self._disk_queue is not None:
			try:
				self._disk_queue.put_nowait(_DISK_STOP)
			except queue.Full:
				try:
					self._disk_queue.get_nowait()
				except queue.Empty:
					pass
				self._disk_queue.put_nowait(_DISK_STOP)

		if self._net_thread:
			self._net_thread.join(timeout=15.0)
		if self._disk_thread:
			self._disk_thread.join(timeout=15.0)

		self.video.stop()
		self.gps.stop()
		self.video.join(timeout=3.0)
		self.gps.join(timeout=2.0)
		self.sock.close()

		if self.stats["dropped_net_queue"] or self.stats["dropped_disk_queue"]:
			logger.info(
				"Colas: descartados UDP=%s disco=%s",
				self.stats["dropped_net_queue"],
				self.stats["dropped_disk_queue"],
			)

	def _send_fragmented(self, img_data, gps, timestamp, seq: int):
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
				seq & 0xFFFFFFFF,
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

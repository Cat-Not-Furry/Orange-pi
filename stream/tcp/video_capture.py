#!/usr/bin/env python3
"""
Captura de video con OpenCV. Hilo que comprime JPEG y pone en cola.
"""

import logging
import queue
import threading
import time

import cv2

logger = logging.getLogger(__name__)


class VideoCapture:
	"""Hilo que captura frames, comprime JPEG y los pone en cola."""

	def __init__(self, width: int, height: int, fps: int, jpeg_quality: int, camera_index: int = 0, max_queue: int = 300):
		self.width = width
		self.height = height
		self.fps = fps
		self.jpeg_quality = jpeg_quality
		self.camera_index = camera_index
		self._queue = queue.Queue(maxsize=max_queue)
		self._stop = threading.Event()
		self._thread = None
		self._cap = None

	def get_frame(self, timeout: float = 0.5):
		"""Obtiene (jpeg_bytes, timestamp, frame_number) o None si timeout."""
		try:
			return self._queue.get(timeout=timeout)
		except queue.Empty:
			return None

	def _run(self):
		interval = 1.0 / self.fps if self.fps > 0 else 0.033
		frame_number = 0
		next_frame_time = time.perf_counter()

		while not self._stop.is_set():
			try:
				if self._cap is None or not self._cap.isOpened():
					self._cap = cv2.VideoCapture(self.camera_index)
					if not self._cap.isOpened():
						logger.warning("Cámara no disponible, reintentando...")
						time.sleep(2)
						continue
					self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
					self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
					self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
					self._cap.set(cv2.CAP_PROP_FPS, self.fps)
					self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

				success, frame = self._cap.read()
				if not success:
					time.sleep(0.1)
					continue

				now = time.perf_counter()
				if now >= next_frame_time:
					ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
					if ret:
						try:
							self._queue.put_nowait((buffer.tobytes(), now, frame_number))
						except queue.Full:
							try:
								self._queue.get_nowait()
							except queue.Empty:
								pass
							try:
								self._queue.put_nowait((buffer.tobytes(), now, frame_number))
							except queue.Full:
								pass
					frame_number += 1
					next_frame_time += interval
					if next_frame_time < now:
						next_frame_time = now + interval

				time.sleep(max(0, next_frame_time - time.perf_counter()))
			except Exception as e:
				logger.warning(f"Video capture error: {e}")
				if self._cap:
					try:
						self._cap.release()
					except Exception:
						pass
					self._cap = None
				time.sleep(1)

		if self._cap:
			try:
				self._cap.release()
			except Exception:
				pass

	def start(self):
		"""Inicia el hilo de captura."""
		self._stop.clear()
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()

	def stop(self):
		"""Detiene el hilo."""
		self._stop.set()

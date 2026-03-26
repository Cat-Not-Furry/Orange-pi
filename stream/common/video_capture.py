#!/usr/bin/env python3
"""
Captura de video con OpenCV: MJPEG, JPEG con calidad/luma/croma, rotación, cola.
"""

import logging
import queue
import threading
import time

import cv2

from stream.common import config

logger = logging.getLogger(__name__)


def _find_camera(indices):
	"""Prueba varios índices hasta encontrar una cámara que entregue frames."""
	for idx in indices:
		logger.info("Probando cámara /dev/video%d...", idx)
		cap = cv2.VideoCapture(idx)
		if cap.isOpened():
			ret, _ = cap.read()
			if ret:
				logger.info("Cámara encontrada en /dev/video%d", idx)
				cap.release()
				return idx
			logger.warning("Índice %d se abrió pero no entrega frames", idx)
		cap.release()
	return None


class VideoCapture:
	"""Hilo que captura frames, comprime JPEG y los pone en cola."""

	def __init__(self):
		self.width = config.FRAME_WIDTH
		self.height = config.FRAME_HEIGHT
		self.fps = config.FPS
		self.camera_indices = config.CAMERA_INDICES
		self.max_queue = config.MAX_QUEUE_SIZE
		self.rotate = config.ROTATE
		self._encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), int(config.JPEG_QUALITY)]
		if hasattr(cv2, "IMWRITE_JPEG_LUMA_QUALITY"):
			self._encode_param.extend(
				[
					int(cv2.IMWRITE_JPEG_LUMA_QUALITY),
					int(config.JPEG_LUMA_QUALITY),
					int(cv2.IMWRITE_JPEG_CHROMA_QUALITY),
					int(config.JPEG_CHROMA_QUALITY),
				]
			)
		self._queue = queue.Queue(maxsize=self.max_queue)
		self._stop = threading.Event()
		self._thread = None
		self._cap = None
		self._current_index = None

	def get_frame(self, timeout: float = 0.5):
		"""Obtiene (jpeg_bytes, timestamp, frame_number) o None si timeout."""
		try:
			return self._queue.get(timeout=timeout)
		except queue.Empty:
			return None

	def _rotate_frame(self, nd_array):
		if self.rotate == 90:
			return cv2.rotate(nd_array, cv2.ROTATE_90_CLOCKWISE)
		if self.rotate == 180:
			return cv2.rotate(nd_array, cv2.ROTATE_180)
		if self.rotate == 270:
			return cv2.rotate(nd_array, cv2.ROTATE_90_COUNTERCLOCKWISE)
		return nd_array

	def _run(self):
		interval = 1.0 / self.fps if self.fps > 0 else 0.033
		frame_number = 0
		next_frame_time = time.perf_counter()

		while not self._stop.is_set():
			try:
				if self._cap is None or not self._cap.isOpened():
					idx = self._current_index
					if idx is None:
						idx = _find_camera(self.camera_indices)
						self._current_index = idx
					if idx is None:
						logger.warning("No se encontró cámara en %s. Reintentando...", self.camera_indices)
						time.sleep(2)
						continue
					self._cap = cv2.VideoCapture(idx)
					if not self._cap.isOpened():
						self._current_index = None
						logger.warning("Cámara /dev/video%d no disponible, buscando otra...", idx)
						time.sleep(2)
						continue
					self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
					self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
					self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
					self._cap.set(cv2.CAP_PROP_FPS, self.fps)
					self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

				success, frame = self._cap.read()
				if not success:
					self._current_index = None
					if self._cap:
						try:
							self._cap.release()
						except Exception:
							pass
						self._cap = None
					time.sleep(0.5)
					continue

				if self.rotate:
					frame = self._rotate_frame(frame)

				now = time.perf_counter()
				if now >= next_frame_time:
					ret, buffer = cv2.imencode(".jpg", frame, self._encode_param)
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

	def join(self, timeout=None):
		if self._thread:
			self._thread.join(timeout=timeout)

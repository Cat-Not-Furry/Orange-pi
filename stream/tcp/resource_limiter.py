#!/usr/bin/env python3
"""
Módulo dinámico que limita el uso de CPU y RAM a un objetivo configurable.
Ajusta FPS, calidad JPEG y resolución según el uso actual del sistema.
"""

import os
import threading
import time
import logging

try:
	import psutil
except ImportError:
	psutil = None

logger = logging.getLogger(__name__)

# Niveles de calidad: menor a mayor carga (width, height, fps, jpeg_quality)
QUALITY_LEVELS = [
	(480, 270, 15, 50),
	(640, 360, 20, 55),
	(640, 360, 30, 60),
	(854, 480, 25, 65),
	(854, 480, 30, 70),
	(1280, 720, 25, 75),
	(1280, 720, 30, 80),
	(1280, 720, 60, 80),
	(1280, 720, 60, 90),
]


class ResourceLimiter:
	"""
	Limita el uso de CPU y RAM a objetivos configurables mediante un bucle
	de retroalimentación que ajusta FPS, calidad JPEG y resolución.
	"""

	def __init__(
		self,
		cpu_target: float = 70,
		ram_target: float = 70,
		target_fps: int = 60,
		adapt_interval_sec: float = 5,
		initial_level: int = 4,
	):
		self.cpu_target = float(os.environ.get("CPU_TARGET_PCT", cpu_target))
		self.ram_target = float(os.environ.get("RAM_TARGET_PCT", ram_target))
		self.target_fps = int(os.environ.get("TARGET_FPS", target_fps))
		self.adapt_interval = float(os.environ.get("ADAPT_INTERVAL_SEC", adapt_interval_sec))
		env_level = os.environ.get("RESOURCE_INITIAL_LEVEL")
		level_val = int(env_level) if env_level is not None else initial_level
		self._level = max(0, min(level_val, len(QUALITY_LEVELS) - 1))
		self._lock = threading.Lock()
		self._params = self._level_to_params(self._level)
		self._stop = threading.Event()
		self._thread = None

	def _level_to_params(self, level: int) -> dict:
		w, h, fps, jpeg = QUALITY_LEVELS[level]
		return {"width": w, "height": h, "fps": fps, "jpeg_quality": jpeg}

	def get_recommended_params(self) -> dict:
		"""Devuelve {fps, jpeg_quality, width, height} según nivel actual."""
		with self._lock:
			return dict(self._params)

	def _adapt(self) -> None:
		if not psutil:
			return
		cpu = psutil.cpu_percent(interval=1)
		mem = psutil.virtual_memory().percent
		with self._lock:
			level = self._level
			if cpu > self.cpu_target or mem > self.ram_target:
				if level > 0:
					level -= 1
					logger.info(f"Recursos altos (CPU={cpu:.0f}%, Mem={mem:.0f}%) -> nivel {level}")
			elif cpu < self.cpu_target * 0.8 and mem < self.ram_target * 0.8:
				if level < len(QUALITY_LEVELS) - 1:
					level += 1
					logger.info(f"Recursos bajos (CPU={cpu:.0f}%, Mem={mem:.0f}%) -> nivel {level}")
			self._level = level
			self._params = self._level_to_params(level)

	def _adaptation_loop(self, callback) -> None:
		while not self._stop.wait(self.adapt_interval):
			self._adapt()
			params = self.get_recommended_params()
			try:
				callback(params)
			except Exception as e:
				logger.warning(f"Callback ResourceLimiter: {e}")

	def start_adaptation_loop(self, callback) -> None:
		"""Inicia un hilo que llama callback(params) cada ADAPT_INTERVAL_SEC."""
		if not psutil:
			logger.warning("psutil no instalado. ResourceLimiter inactivo.")
			return
		self._stop.clear()
		self._thread = threading.Thread(
			target=self._adaptation_loop,
			args=(callback,),
			daemon=True,
		)
		self._thread.start()
		logger.info(
			f"ResourceLimiter activo: CPU target={self.cpu_target}%, RAM target={self.ram_target}%"
		)

	def stop(self) -> None:
		"""Detiene el loop de adaptación."""
		self._stop.set()

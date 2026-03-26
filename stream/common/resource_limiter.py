#!/usr/bin/env python3
"""
Telemetría simple de CPU y memoria (psutil). Sin bucle de adaptación.
"""

import psutil


class ResourceLimiter:
	"""Exponer uso actual frente a umbrales configurables."""

	def __init__(self, max_cpu=70, max_mem=80):
		self.max_cpu = max_cpu
		self.max_mem = max_mem

	def get_usage(self):
		return psutil.cpu_percent(interval=None), psutil.virtual_memory().percent

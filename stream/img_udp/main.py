#!/usr/bin/env python3
"""
Punto de entrada Orange Pi: emisor UDP de imágenes JPEG fragmentadas.
La sesión (nombre de subcarpeta en recordings/) la define esta Pi salvo SESSION_ID en env.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime

from stream.common import config
from stream.img_udp.sender import UDPImageSender

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _default_session_id() -> str:
	return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def main():
	session_id = os.environ.get("SESSION_ID", "").strip() or _default_session_id()
	print(f"Sesión (Orange Pi): {session_id}")
	print(
		f"Imágenes análisis locales: bajo recordings/{session_id}/{config.ANALYSIS_SUBDIR}/"
	)
	try:
		sender = UDPImageSender(session_id)
	except ValueError as e:
		print(e, file=sys.stderr)
		return 1
	sender.start()

	def signal_handler(_sig, _frame):
		print("\nDeteniendo...")
		sender.stop()
		sys.exit(0)

	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	print("Emisor UDP (imágenes) iniciado. Ctrl+C para detener.")
	try:
		while sender.is_alive():
			time.sleep(0.5)
	except KeyboardInterrupt:
		sender.stop()
	sender.join(timeout=5.0)
	return 0


if __name__ == "__main__":
	sys.exit(main())

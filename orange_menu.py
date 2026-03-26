#!/usr/bin/env python3
"""
Menú Orange Pi: envío UDP de imágenes JPEG fragmentadas; IP del host (laptop).

Desde la raíz del repo: python orange_menu.py

En la laptop: python host_menu.py (o stream/img_udp/receiver.py).
"""

import os
import subprocess
import sys
from typing import Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _leer_ip_host() -> Optional[str]:
	print("\nIP del host (laptop) en la LAN, ej. 192.168.1.50")
	try:
		ip = input("UDP_DEST_IP / UDP_HOST: ").strip()
	except EOFError:
		return None
	if not ip:
		print("Se necesita una IP.")
		return None
	return ip


def _submenu_calidad() -> Optional[Dict[str, str]]:
	print("\n--- Calidad de captura (emisor) ---")
	print("  1. Máxima calidad (1920x1080 @ 60 fps)")
	print("  2. Alta (1280x720 @ 60 fps)")
	print("  3. Predeterminado (variables FRAME_WIDTH / FPS o 640x360 @ 15)")
	print("  0. Volver")
	try:
		o = input("Selecciona: ").strip()
		n = int(o) if o else 0
	except (ValueError, EOFError):
		n = 0
	if n == 1:
		return {"IMG_UDP_QUALITY_MAX": "1"}
	if n == 2:
		return {"IMG_UDP_QUALITY_SUPERIOR": "1"}
	if n == 3:
		return {}
	return None


def _lanzar_img_udp(env_extra: Dict[str, str]) -> int:
	env = os.environ.copy()
	env.update(env_extra)
	cmd = [sys.executable, "-m", "stream.img_udp.main"]
	print("\nIniciando emisor UDP (imágenes)… Ctrl+C para detener.\n")
	return subprocess.run(cmd, cwd=PROJECT_ROOT, env=env).returncode


def main() -> int:
	print("\n=== Orange Pi — envío UDP imágenes + GPS al host ===\n")
	print("  1. Iniciar emisor (elige calidad después)")
	print("  0. Salir")

	try:
		o = input("\nSelecciona [0-1]: ").strip()
		top = int(o) if o else 0
	except (ValueError, EOFError):
		top = 0

	if top == 0:
		print("Hasta luego.")
		return 0
	if top != 1:
		print("Opción no válida.")
		return 1

	ip = _leer_ip_host()
	if not ip:
		return 1

	qual = _submenu_calidad()
	if qual is None:
		print("Cancelado.")
		return 0

	env = {"UDP_DEST_IP": ip, **qual}
	return _lanzar_img_udp(env)


if __name__ == "__main__":
	sys.exit(main())

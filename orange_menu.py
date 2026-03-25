#!/usr/bin/env python3
"""
Menú Orange Pi: elige TCP o UDP e introduce la IP del host (laptop) para enviar el stream.

Desde la raíz del repo: python orange_menu.py

En la laptop debe estar escuchando: python host_menu.py (mismo perfil TCP/UDP).
"""

import os
import subprocess
import sys
from typing import Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _leer_ip_host() -> Optional[str]:
	print("\nIP del host (laptop) en la LAN, ej. 192.168.1.50")
	try:
		ip = input("TCP_HOST / UDP_HOST: ").strip()
	except EOFError:
		return None
	if not ip:
		print("Se necesita una IP.")
		return None
	return ip


def _submenu_tcp_calidad() -> Optional[Dict[str, str]]:
	print("\n--- TCP: calidad ---")
	print("  1. Máxima calidad (1920x1080 @ 60 fps)")
	print("  2. Calidad normal (640x360 @ 30 fps)")
	print("  0. Volver")
	try:
		o = input("Selecciona: ").strip()
		n = int(o) if o else 0
	except (ValueError, EOFError):
		n = 0
	if n == 1:
		return {"TCP_QUALITY_MAX": "1"}
	if n == 2:
		return {"TCP_QUALITY_NORMAL": "1"}
	return None


def _submenu_udp_calidad() -> Optional[Dict[str, str]]:
	print("\n--- UDP: calidad ---")
	print("  1. Máxima calidad (1920x1080 @ 60 fps)")
	print("  2. Máxima transmisión / fluido (1280x720 @ 60 fps)")
	print("  0. Volver")
	try:
		o = input("Selecciona: ").strip()
		n = int(o) if o else 0
	except (ValueError, EOFError):
		n = 0
	if n == 1:
		return {"UDP_QUALITY_MAX": "1"}
	if n == 2:
		return {"UDP_QUALITY_SUPERIOR": "1"}
	return None


def _lanzar_tcp(env_extra: Dict[str, str]) -> int:
	env = os.environ.copy()
	env.update(env_extra)
	cmd = [sys.executable, "-m", "stream.tcp.main"]
	print("\nIniciando cliente TCP… Ctrl+C para detener.\n")
	return subprocess.run(cmd, cwd=PROJECT_ROOT, env=env).returncode


def _lanzar_udp(env_extra: Dict[str, str]) -> int:
	env = os.environ.copy()
	env.update(env_extra)
	cmd = [sys.executable, "-m", "stream.udp.main"]
	print("\nIniciando cliente UDP… Ctrl+C para detener.\n")
	return subprocess.run(cmd, cwd=PROJECT_ROOT, env=env).returncode


def main() -> int:
	print("\n=== Orange Pi — envío de video/GPS al host ===\n")
	print("  1. TCP (entrega confiable)")
	print("  2. UDP (baja latencia)")
	print("  0. Salir")

	try:
		o = input("\nSelecciona [0-2]: ").strip()
		top = int(o) if o else 0
	except (ValueError, EOFError):
		top = 0

	if top == 0:
		print("Hasta luego.")
		return 0
	if top not in (1, 2):
		print("Opción no válida.")
		return 1

	ip = _leer_ip_host()
	if not ip:
		return 1

	if top == 1:
		qual = _submenu_tcp_calidad()
		if qual is None:
			print("Cancelado.")
			return 0
		env = {"TCP_HOST": ip, **qual}
		return _lanzar_tcp(env)

	qual = _submenu_udp_calidad()
	if qual is None:
		print("Cancelado.")
		return 0
	env = {"UDP_HOST": ip, **qual}
	return _lanzar_udp(env)


if __name__ == "__main__":
	sys.exit(main())

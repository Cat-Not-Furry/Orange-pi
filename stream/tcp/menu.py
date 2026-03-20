#!/usr/bin/env python3
"""
Menú interactivo para streaming. Tres modos: TCP máxima/superior, TCP normal, HTTP máxima.
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
WEB_CAM = os.path.join(SCRIPT_DIR, "web-cam.py")

MODOS = [
	{
		"nombre": "TCP Calidad máxima/superior (1920x1080 o 1280x720 @ 60fps)",
		"cmd": [sys.executable, "-m", "stream.tcp.main"],
		"cwd": PROJECT_ROOT,
		"env": {"TCP_QUALITY_MAX": "1"},
	},
	{
		"nombre": "TCP Calidad normal (640x360 @ 30fps)",
		"cmd": [sys.executable, "-m", "stream.tcp.main"],
		"cwd": PROJECT_ROOT,
		"env": {"TCP_QUALITY_NORMAL": "1"},
	},
	{
		"nombre": "HTTP Máxima calidad (1920x1080 @ 60fps)",
		"cmd": [sys.executable, WEB_CAM],
		"cwd": SCRIPT_DIR,
		"env": {"MAX_QUALITY_MODE": "1"},
	},
]


def mostrar_menu():
	print("\n=== Stream de video (Orange Pi) ===\n")
	for i, modo in enumerate(MODOS, 1):
		print(f"  {i}. {modo['nombre']}")
	print("  0. Salir")
	print("\n  TCP: configura TCP_HOST=IP_LAPTOP antes. En laptop: python receiver.py")
	print("  HTTP: en laptop: python recorder.py --host IP_ORANGE_PI --port 5000\n")


def ejecutar_modo(numero: int) -> int:
	if numero == 0:
		return 0
	if 1 <= numero <= len(MODOS):
		modo = MODOS[numero - 1]
		env = os.environ.copy()
		env.update(modo["env"])
		print(f"\nEjecutando: {modo['nombre']}")
		print("Ctrl+C para detener.\n")
		return subprocess.run(modo["cmd"], env=env, cwd=modo["cwd"]).returncode
	return 1


def main():
	while True:
		mostrar_menu()
		try:
			entrada = input("Selecciona [0-{}]: ".format(len(MODOS))).strip()
			opcion = int(entrada) if entrada else 0
		except (ValueError, EOFError):
			opcion = 0
		if opcion == 0:
			print("Hasta luego.")
			return 0
		ejecutar_modo(opcion)


if __name__ == "__main__":
	sys.exit(main())

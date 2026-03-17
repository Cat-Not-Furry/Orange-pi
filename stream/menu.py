#!/usr/bin/env python3
"""
Menú interactivo para el servidor de streaming.
Ejecutar: python menu.py
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_CAM = os.path.join(SCRIPT_DIR, "web-cam.py")

MODOS = [
	{
		"nombre": "Normal (HTTP, 1280x720, 30fps)",
		"env": {"FRAME_WIDTH": "1280", "FRAME_HEIGHT": "720", "FPS": "30", "JPEG_QUALITY": "80"},
	},
	{
		"nombre": "Alcance largo 80m (640x360, 15fps)",
		"env": {"LONG_RANGE_MODE": "1"},
	},
	{
		"nombre": "Red inestable (buffer + menor calidad)",
		"env": {"UNSTABLE_NETWORK_MODE": "1", "FRAME_BUFFER_SIZE": "8"},
	},
	{
		"nombre": "Recursos dinámicos (CPU/RAM ~70%)",
		"env": {"DYNAMIC_RESOURCES": "1", "FRAME_WIDTH": "1280", "FRAME_HEIGHT": "720", "FPS": "30", "JPEG_QUALITY": "80"},
	},
	{
		"nombre": "UDP (transmitir video por red)",
		"env": {"UDP_ENABLED": "1", "FRAME_WIDTH": "640", "FRAME_HEIGHT": "360", "FPS": "30", "JPEG_QUALITY": "60"},
	},
	{
		"nombre": "HTTPS (certificado adhoc)",
		"env": {"SSL_ADHOC": "1", "FRAME_WIDTH": "1280", "FRAME_HEIGHT": "720", "FPS": "30", "JPEG_QUALITY": "80"},
	},
]


def mostrar_menu():
	print("\n=== Stream de video ===\n")
	for i, modo in enumerate(MODOS, 1):
		print(f"  {i}. {modo['nombre']}")
	print("  0. Salir")
	print()


def ejecutar_modo(numero: int) -> int:
	if numero == 0:
		return 0
	if 1 <= numero <= len(MODOS):
		modo = MODOS[numero - 1]
		env = os.environ.copy()
		env.update(modo["env"])
		print(f"\nEjecutando: {modo['nombre']}")
		print("Ctrl+C para detener.\n")
		return subprocess.run([sys.executable, WEB_CAM], env=env).returncode
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

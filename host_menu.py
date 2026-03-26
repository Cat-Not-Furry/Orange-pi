#!/usr/bin/env python3
"""
Menú del host (laptop): receptor UDP imágenes (JPEG + GPS).

Desde la raíz del repo: python host_menu.py

En Orange Pi usa: python orange_menu.py (introduce la IP de esta laptop).
"""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STREAM_DIR = os.path.join(PROJECT_ROOT, "stream")
RECORDINGS_BASE = os.path.join(PROJECT_ROOT, "recordings")
RECEIVER = os.path.join(STREAM_DIR, "img_udp", "receiver.py")

MODOS = [
	{
		"nombre": "UDP imágenes — máxima calidad (1080p60, perfil emisor)",
		"hint_pi": "orange_menu.py → máxima calidad",
		"env": {},
	},
	{
		"nombre": "UDP imágenes — calidad alta (720p60, perfil emisor)",
		"hint_pi": "orange_menu.py → calidad alta",
		"env": {},
	},
	{
		"nombre": "UDP imágenes — calidad por defecto (resolución en .env / config)",
		"hint_pi": "orange_menu.py → predeterminado",
		"env": {},
	},
]


def _mostrar_emparejamiento(modo: dict) -> None:
	print("\n" + "─" * 60)
	print("Orange Pi: ejecuta en la raíz del mismo repo:")
	print("  python orange_menu.py")
	print("Introduce la IP de esta laptop y elige la opción que coincida:")
	print(f"  → {modo['hint_pi']}")
	print("─" * 60 + "\n")


def _lanzar_receptor(modo: dict) -> int:
	env = os.environ.copy()
	prev = env.get("PYTHONPATH", "")
	env["PYTHONPATH"] = PROJECT_ROOT + (os.pathsep + prev if prev else "")
	env.update(modo.get("env") or {})
	cmd = [
		sys.executable,
		RECEIVER,
		"--recordings-base",
		RECORDINGS_BASE,
	]
	print(f"\nEjecutando: {' '.join(cmd)}\n")
	return subprocess.run(cmd, cwd=STREAM_DIR, env=env).returncode


def main() -> int:
	print("\n=== Host (laptop) — receptor UDP imágenes ===\n")
	for i, modo in enumerate(MODOS, 1):
		print(f"  {i}. {modo['nombre']}")
	print("  0. Salir\n")

	try:
		entrada = input("Selecciona [0-{}]: ".format(len(MODOS))).strip()
		opcion = int(entrada) if entrada else 0
	except (ValueError, EOFError):
		opcion = 0

	if opcion == 0:
		print("Hasta luego.")
		return 0
	if not (1 <= opcion <= len(MODOS)):
		print("Opción no válida.")
		return 1

	modo = dict(MODOS[opcion - 1])
	print(f"\nModo: {modo['nombre']}")
	_mostrar_emparejamiento(modo)
	input("Pulsa Enter para iniciar el receptor en esta laptop… ")
	return _lanzar_receptor(modo)


if __name__ == "__main__":
	sys.exit(main())

#!/usr/bin/env python3
"""
Menú del host (laptop): qué protocolo escuchar — TCP o UDP y el perfil de calidad en Orange Pi.

Desde la raíz del repo: python host_menu.py

En Orange Pi usa: python orange_menu.py (introduce la IP de esta laptop).
"""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STREAM_DIR = os.path.join(PROJECT_ROOT, "stream")
RECEIVER = os.path.join(STREAM_DIR, "receiver.py")

MODOS = [
	{
		"nombre": "TCP — máxima calidad (entrega confiable de paquetes)",
		"protocol": "tcp",
		"hint_pi": "orange_menu.py → TCP → máxima calidad",
	},
	{
		"nombre": "TCP — calidad normal (entrega confiable de paquetes)",
		"protocol": "tcp",
		"hint_pi": "orange_menu.py → TCP → calidad normal",
	},
	{
		"nombre": "UDP — máxima calidad (baja latencia)",
		"protocol": "udp",
		"hint_pi": "orange_menu.py → UDP → máxima calidad",
	},
	{
		"nombre": "UDP — máxima transmisión / fluido (baja latencia, 720p60)",
		"protocol": "udp",
		"hint_pi": "orange_menu.py → UDP → máxima transmisión",
	},
]


def _mostrar_emparejamiento(modo: dict) -> None:
	print("\n" + "─" * 60)
	print("Orange Pi: ejecuta en la raíz del mismo repo:")
	print("  python orange_menu.py")
	print("Introduce la IP de esta laptop y elige la opción que coincida:")
	print(f"  → {modo['hint_pi']}")
	print("─" * 60 + "\n")


def _lanzar_receptor(protocol: str) -> int:
	env = os.environ.copy()
	prev = env.get("PYTHONPATH", "")
	env["PYTHONPATH"] = PROJECT_ROOT + (os.pathsep + prev if prev else "")
	cmd = [
		sys.executable,
		RECEIVER,
		protocol,
		"--output-dir",
		os.path.join(STREAM_DIR, "recordings"),
		"--gpx-dir",
		STREAM_DIR,
	]
	print(f"\nEjecutando: {' '.join(cmd)}\n")
	return subprocess.run(cmd, cwd=STREAM_DIR, env=env).returncode


def main() -> int:
	print("\n=== Host (laptop) — receptor de stream ===\n")
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

	modo = MODOS[opcion - 1]
	print(f"\nModo: {modo['nombre']}")
	_mostrar_emparejamiento(modo)
	input("Pulsa Enter para iniciar el receptor en esta laptop… ")
	return _lanzar_receptor(modo["protocol"])


if __name__ == "__main__":
	sys.exit(main())

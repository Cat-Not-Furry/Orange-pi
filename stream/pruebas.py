#!/usr/bin/env python3
"""
Script de pruebas: ejecuta el servidor de streaming con distintas configuraciones.
Uso: python pruebas.py [--width W] [--height H] [--fps F] [--jpeg J]
     o sin argumentos para ver las configuraciones sugeridas.

Ejemplo: python pruebas.py --width 640 --height 360 --fps 20 --jpeg 60
"""

import argparse
import os
import subprocess
import sys

CONFIGURACIONES_SUGERIDAS = [
	{"width": 1280, "height": 720, "fps": 30, "jpeg": 80},
	{"width": 854, "height": 480, "fps": 25, "jpeg": 70},
	{"width": 640, "height": 360, "fps": 20, "jpeg": 60},
	{"width": 640, "height": 360, "fps": 15, "jpeg": 50},
	{"width": 480, "height": 270, "fps": 15, "jpeg": 50},
]


def ejecutar_servidor(
	width: int, height: int, fps: int, jpeg: int, https: bool = False,
	crt_file: str = "", key_file: str = ""
) -> int:
	"""Lanza el servidor con la configuración indicada."""
	env = os.environ.copy()
	env["FRAME_WIDTH"] = str(width)
	env["FRAME_HEIGHT"] = str(height)
	env["FPS"] = str(fps)
	env["JPEG_QUALITY"] = str(jpeg)
	if https:
		if crt_file and key_file:
			env["SSL_CRT_FILE"] = crt_file
			env["SSL_KEY_FILE"] = key_file
		else:
			env["SSL_ADHOC"] = "1"
	script_dir = os.path.dirname(os.path.abspath(__file__))
	web_cam = os.path.join(script_dir, "web-cam.py")
	return subprocess.run([sys.executable, web_cam], env=env).returncode


def main():
	parser = argparse.ArgumentParser(description="Ejecutar servidor de streaming con configuración")
	parser.add_argument("--width", type=int, help="Ancho de frame")
	parser.add_argument("--height", type=int, help="Alto de frame")
	parser.add_argument("--fps", type=int, help="Frames por segundo")
	parser.add_argument("--jpeg", type=int, help="Calidad JPEG 0-100")
	parser.add_argument("--listar", action="store_true", help="Listar configuraciones sugeridas")
	parser.add_argument("--https", action="store_true", help="Usar HTTPS (adhoc si no se pasan --crt/--key)")
	parser.add_argument("--crt", type=str, help="Ruta al certificado PEM (requiere --key)")
	parser.add_argument("--key", type=str, help="Ruta a la clave privada PEM (requiere --crt)")
	args = parser.parse_args()

	if args.listar:
		print("Configuraciones sugeridas para pruebas:\n")
		for i, cfg in enumerate(CONFIGURACIONES_SUGERIDAS, 1):
			cmd = (
				f"python pruebas.py --width {cfg['width']} --height {cfg['height']} "
				f"--fps {cfg['fps']} --jpeg {cfg['jpeg']}"
			)
			print(f"  {i}. {cfg['width']}x{cfg['height']} @ {cfg['fps']}fps, JPEG {cfg['jpeg']}%")
			print(f"     {cmd}\n")
		return 0

	if args.width is None or args.height is None or args.fps is None or args.jpeg is None:
		print("Usa --listar para ver configuraciones sugeridas.")
		print("Ejemplo: python pruebas.py --width 640 --height 360 --fps 20 --jpeg 60")
		return 1

	if args.https and (bool(args.crt) != bool(args.key)):
		print("Error: --crt y --key deben usarse juntos.")
		return 1

	https = args.https
	crt_file = args.crt or ""
	key_file = args.key or ""

	modo = "HTTPS" if https else "HTTP"
	print(f"Ejecutando: {args.width}x{args.height} @ {args.fps}fps, JPEG {args.jpeg}% ({modo})")
	print("Ctrl+C para detener. Anota métricas en RESULTADOS.md\n")
	return ejecutar_servidor(args.width, args.height, args.fps, args.jpeg, https, crt_file, key_file)


if __name__ == "__main__":
	sys.exit(main())

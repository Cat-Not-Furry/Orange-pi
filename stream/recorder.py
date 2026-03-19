#!/usr/bin/env python3
"""
Grabador de stream para laptop. Conecta al Orange Pi, recibe el stream MJPEG
y guarda el video en disco local. Ejecutar en la laptop (no en Orange Pi).

Uso:
    python recorder.py --host 192.168.1.100 --port 5000
    python recorder.py --url http://192.168.1.100:5000/video_feed --output-dir ./videos
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


try:
	import cv2
	import numpy as np
except ImportError:
	print("Error: opencv-python no instalado. Ejecuta: pip install opencv-python")
	sys.exit(1)


def build_stream_url(host: str, port: int, use_https: bool = False) -> str:
	"""Construye URL del stream de video."""
	protocol = "https" if use_https else "http"
	return f"{protocol}://{host}:{port}/video_feed"


def parse_mjpeg_stream(stream):
	"""Generador que parsea frames JPEG del stream MJPEG."""
	boundary = b"--frame"
	buffer = b""
	content_length_re = re.compile(rb"Content-Length:\s*(\d+)", re.IGNORECASE)
	chunk_size = 8192

	while True:
		try:
			chunk = stream.read(chunk_size)
		except Exception:
			break
		if not chunk:
			break
		buffer += chunk
		while True:
			start = buffer.find(boundary)
			if start == -1:
				if len(buffer) > 65536:
					buffer = buffer[-32768:]
				break
			buffer = buffer[start + len(boundary):]
			header_end = buffer.find(b"\r\n\r\n")
			if header_end == -1:
				break
			headers = buffer[:header_end]
			buffer = buffer[header_end + 4:]
			match = content_length_re.search(headers)
			if not match:
				continue
			length = int(match.group(1))
			while len(buffer) < length:
				try:
					more = stream.read(chunk_size)
					if not more:
						return
					buffer += more
				except Exception:
					return
			jpeg_data = buffer[:length]
			buffer = buffer[length:]
			frame = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
			if frame is not None:
				yield frame


def init_video_writer(base_path: str, width: int, height: int, fps: float):
	"""Crea VideoWriter. Prueba H264, MP4V, MJPEG."""
	codecs = [
		("avc1", ".mp4"),
		("H264", ".mp4"),
		("mp4v", ".mp4"),
		("MJPG", ".avi"),
	]
	for fourcc_str, ext in codecs:
		out_path = base_path + ext
		fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
		writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
		if writer.isOpened():
			return writer, out_path
		writer.release()
	return None, None


def record_stream(
	url: str,
	output_dir: str,
	retry_interval: float = 5.0,
):
	"""Conecta al stream, reintenta hasta conectarse, y graba en archivo."""
	os.makedirs(output_dir, exist_ok=True)
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	base_path = os.path.join(output_dir, f"recording_{timestamp}")

	writer = None
	stream = None
	width = height = fps = 0
	frame_count = 0
	start_time = None

	while True:
		try:
			req = Request(url, headers={"User-Agent": "StreamRecorder/1.0"})
			stream = urlopen(req, timeout=10)
			break
		except (URLError, HTTPError, OSError) as e:
			print(f"Esperando conexión con {url}... ({e})")
			time.sleep(retry_interval)

	print(f"Conectado. Grabando en {output_dir}/")
	print("Ctrl+C para detener.\n")

	try:
		for frame in parse_mjpeg_stream(stream):
			h, w = frame.shape[:2]
			if writer is None:
				fps = 30.0
				writer, out_path = init_video_writer(base_path, w, h, fps)
				if writer is None:
					print("Error: no se pudo crear VideoWriter.")
					return 1
				width, height = w, h
				start_time = time.time()
				print(f"Guardando: {out_path} ({w}x{h} @ {fps}fps)")

			if (w, h) != (width, height):
				continue
			writer.write(frame)
			frame_count += 1
			if frame_count % 300 == 0:
				elapsed = time.time() - start_time
				actual_fps = frame_count / elapsed if elapsed > 0 else 0
				print(f"Frames: {frame_count}, FPS: {actual_fps:.1f}")
	except KeyboardInterrupt:
		pass
	finally:
		if stream:
			try:
				stream.close()
			except Exception:
				pass
		if writer and writer.isOpened():
			writer.release()
			print(f"\nGrabación finalizada. {frame_count} frames guardados.")

	return 0


def main():
	parser = argparse.ArgumentParser(
		description="Grabar stream de video desde Orange Pi en la laptop."
	)
	parser.add_argument("--host", type=str, help="IP del Orange Pi")
	parser.add_argument("--port", type=int, default=5000, help="Puerto (default: 5000)")
	parser.add_argument("--url", type=str, help="URL completa del stream (ej. http://192.168.1.100:5000/video_feed)")
	parser.add_argument("--output-dir", type=str, default="./recordings", help="Directorio de salida")
	parser.add_argument("--retry", type=float, default=5.0, help="Segundos entre reintentos de conexión")
	parser.add_argument("--https", action="store_true", help="Usar HTTPS")
	args = parser.parse_args()

	if args.url:
		url = args.url
	else:
		if not args.host:
			print("Error: especifica --host o --url")
			return 1
		url = build_stream_url(args.host, args.port, args.https)

	return record_stream(url, args.output_dir, args.retry)


if __name__ == "__main__":
	sys.exit(main())

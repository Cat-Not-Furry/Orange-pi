#!/usr/bin/env python3
"""
Cliente de prueba para recibir video MJPEG por UDP.
Uso: python udp_client.py [--port 5005] [--bind 0.0.0.0]
"""

import argparse
import struct
import socket
import sys

try:
	import cv2
	import numpy as np
except ImportError:
	cv2 = None
	np = None

HEADER_SIZE = 8
CHUNK_MAX = 1400


def main():
	parser = argparse.ArgumentParser(description="Recibir video MJPEG por UDP")
	parser.add_argument("--port", type=int, default=5005, help="Puerto de escucha")
	parser.add_argument("--bind", type=str, default="0.0.0.0", help="IP de bind")
	args = parser.parse_args()

	if not cv2 or not np:
		print("Se requiere opencv-python: pip install opencv-python")
		sys.exit(1)

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
	sock.bind((args.bind, args.port))
	print(f"Escuchando en {args.bind}:{args.port}")

	frames = {}
	while True:
		data, _ = sock.recvfrom(65535)
		if len(data) < HEADER_SIZE:
			continue
		frame_id, chunk_idx, total_chunks = struct.unpack(">IHH", data[:HEADER_SIZE])
		payload = data[HEADER_SIZE:]
		if frame_id not in frames:
			frames[frame_id] = [None] * total_chunks
		if chunk_idx < total_chunks:
			frames[frame_id][chunk_idx] = payload
		complete = all(frames[frame_id][i] is not None for i in range(total_chunks))
		if complete:
			frame_bytes = b"".join(frames[frame_id])
			del frames[frame_id]
			img = np.frombuffer(frame_bytes, dtype=np.uint8)
			img = cv2.imdecode(img, cv2.IMREAD_COLOR)
			if img is not None:
				cv2.imshow("UDP Stream", img)
				if cv2.waitKey(1) & 0xFF == ord("q"):
					break
		# Limpiar frames antiguos
		if len(frames) > 10:
			old = min(frames.keys())
			del frames[old]

	sock.close()
	cv2.destroyAllWindows()


if __name__ == "__main__":
	main()

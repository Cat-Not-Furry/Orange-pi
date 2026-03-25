#!/usr/bin/env python3
"""
Receptor para laptop: TCP o UDP. Recibe video+GPS del Orange Pi, muestra en tiempo real,
graba con FPS correcto y exporta GPX.

Uso:
	python receiver.py [tcp|udp] [--port N] [--output-dir DIR] [--gpx-dir DIR]
"""

import argparse
import os
import socket
import struct
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np

from stream.udp.udp_sender import UDP_HEADER_FORMAT, UDP_HEADER_SIZE

# Formato de paquete TCP: [4B len_jpeg][8B timestamp][8B lat][8B lon][4B alt][1B quality][2B satellites][jpeg]
META_FORMAT = ">dddfBH"
META_SIZE = struct.calcsize(META_FORMAT)
SEGMENT_DURATION_SEC = 60


def recv_exact(sock, n):
	"""Lee exactamente n bytes."""
	buf = b""
	while len(buf) < n:
		chunk = sock.recv(n - len(buf))
		if not chunk:
			return None
		buf += chunk
	return buf


def read_packet(sock):
	"""Lee un paquete TCP completo. Devuelve (frame, timestamp, lat, lon, alt) o None."""
	header = recv_exact(sock, 4)
	if not header:
		return None
	jpeg_len = struct.unpack(">I", header)[0]
	if jpeg_len > 10 * 1024 * 1024:
		return None
	meta = recv_exact(sock, META_SIZE)
	if not meta:
		return None
	timestamp, lat, lon, alt, quality, satellites = struct.unpack(META_FORMAT, meta)
	jpeg_data = recv_exact(sock, jpeg_len)
	if not jpeg_data:
		return None
	frame = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
	if frame is None:
		return None
	return frame, timestamp, lat, lon, alt


def compute_fps(timestamps, window=30):
	"""FPS efectivo desde diferencias de timestamp."""
	if len(timestamps) < 2:
		return 30.0
	diffs = []
	for i in range(1, min(len(timestamps), window + 1)):
		dt = timestamps[i] - timestamps[i - 1]
		if dt > 0:
			diffs.append(1.0 / dt)
	if not diffs:
		return 30.0
	return sum(diffs) / len(diffs)


def init_video_writer(base_path, width, height, fps):
	"""Crea VideoWriter. Prueba H264, MP4V, MJPEG."""
	codecs = [("avc1", ".mp4"), ("H264", ".mp4"), ("mp4v", ".mp4"), ("MJPG", ".avi")]
	for fourcc_str, ext in codecs:
		out_path = base_path + ext
		fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
		writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
		if writer.isOpened():
			return writer, out_path
		writer.release()
	return None, None


def write_gpx_point(f, lat, lon, alt, timestamp):
	"""Escribe un trkpt en GPX."""
	ts_iso = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%SZ")
	f.write(f'    <trkpt lat="{lat:.8f}" lon="{lon:.8f}">\n')
	f.write(f'      <ele>{alt:.2f}</ele>\n')
	f.write(f'      <time>{ts_iso}</time>\n')
	f.write("    </trkpt>\n")


def _recording_loop_body(
	frame,
	timestamp,
	lat,
	lon,
	alt,
	timestamps,
	writer,
	out_path,
	segment_start,
	width,
	height,
	output_dir,
	gpx_file,
	window_title,
):
	"""Un frame decodificado: actualiza grabación, GPX y preview. Devuelve (writer, out_path, segment_start, width, height)."""
	h, w = frame.shape[:2]
	timestamps.append(timestamp)
	fps = compute_fps(timestamps)

	if writer is None:
		segment_start = time.time()
		ts = datetime.now().strftime("%Y%m%d_%H%M%S")
		base = os.path.join(output_dir, f"recording_{ts}")
		writer, out_path = init_video_writer(base, w, h, fps)
		if writer is None:
			print("Error: no se pudo crear VideoWriter")
			return writer, out_path, segment_start, width, height, True
		width, height = w, h
		print(f"Grabando: {out_path} ({w}x{h} @ {fps:.1f}fps)")

	if (w, h) == (width, height):
		writer.write(frame)
	elif w > 0 and h > 0:
		resized = cv2.resize(frame, (width, height))
		writer.write(resized)

	if lat != 0 or lon != 0:
		write_gpx_point(gpx_file, lat, lon, alt, timestamp)

	cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
	cv2.imshow(window_title, frame)
	if cv2.waitKey(1) & 0xFF == ord("q"):
		return writer, out_path, segment_start, width, height, True

	if segment_start and (time.time() - segment_start) >= SEGMENT_DURATION_SEC:
		if writer and writer.isOpened():
			writer.release()
			writer = None
		segment_start = time.time()
		ts = datetime.now().strftime("%Y%m%d_%H%M%S")
		base = os.path.join(output_dir, f"recording_{ts}")
		writer, out_path = init_video_writer(base, width, height, fps)
		if writer:
			print(f"Nuevo segmento: {out_path}")

	return writer, out_path, segment_start, width, height, False


def run_tcp(port, output_dir, gpx_dir):
	os.makedirs(output_dir, exist_ok=True)
	os.makedirs(gpx_dir, exist_ok=True)

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server.bind(("0.0.0.0", port))
	server.listen(1)
	print(f"[TCP] Esperando conexión en puerto {port}...")

	conn, addr = server.accept()
	print(f"[TCP] Conectado desde {addr}")

	conn.settimeout(30)
	timestamps = deque(maxlen=60)
	writer = None
	out_path = None
	segment_start = None
	width = height = 0
	gpx_path = os.path.join(gpx_dir, f"trayectoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gpx")
	gpx_file = open(gpx_path, "w", encoding="utf-8")
	gpx_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	gpx_file.write('<gpx version="1.1" creator="stream-receiver">\n')
	gpx_file.write("  <trk><trkseg>\n")

	try:
		while True:
			packet = read_packet(conn)
			if packet is None:
				break
			frame, timestamp, lat, lon, alt = packet
			writer, out_path, segment_start, width, height, stop = _recording_loop_body(
				frame,
				timestamp,
				lat,
				lon,
				alt,
				timestamps,
				writer,
				out_path,
				segment_start,
				width,
				height,
				output_dir,
				gpx_file,
				"Stream TCP",
			)
			if stop:
				break
	except Exception as e:
		print(f"Error: {e}")
	finally:
		if writer and writer.isOpened():
			writer.release()
		gpx_file.write("  </trkseg></trk>\n</gpx>\n")
		gpx_file.close()
		cv2.destroyAllWindows()
		conn.close()
		server.close()
		print(f"GPX guardado: {gpx_path}")


def run_udp(port, output_dir, gpx_dir):
	os.makedirs(output_dir, exist_ok=True)
	os.makedirs(gpx_dir, exist_ok=True)

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(("0.0.0.0", port))
	print(f"[UDP] Escuchando en puerto {port}...")

	timestamps = deque(maxlen=60)
	writer = None
	out_path = None
	segment_start = None
	width = height = 0
	gpx_path = os.path.join(gpx_dir, f"trayectoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gpx")
	gpx_file = open(gpx_path, "w", encoding="utf-8")
	gpx_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	gpx_file.write('<gpx version="1.1" creator="stream-receiver">\n')
	gpx_file.write("  <trk><trkseg>\n")

	buffers = {}
	last_clean = time.monotonic()

	try:
		while True:
			try:
				data, addr = sock.recvfrom(65507)
			except InterruptedError:
				continue

			if len(data) < UDP_HEADER_SIZE:
				continue

			meta = struct.unpack(UDP_HEADER_FORMAT, data[:UDP_HEADER_SIZE])
			seq, frag_count, frag_idx, timestamp, lat, lon, alt, _quality, _sats = meta
			payload = data[UDP_HEADER_SIZE:]

			if frag_count == 0 or frag_idx >= frag_count:
				continue

			now = time.monotonic()
			if seq not in buffers:
				buffers[seq] = {
					"count": frag_count,
					"parts": [None] * frag_count,
					"ts": timestamp,
					"lat": lat,
					"lon": lon,
					"alt": alt,
					"t": now,
				}
			buf = buffers[seq]
			buf["ts"] = timestamp
			buf["lat"] = lat
			buf["lon"] = lon
			buf["alt"] = alt
			buf["t"] = now
			if buf["parts"][frag_idx] is None:
				buf["parts"][frag_idx] = payload

			if all(p is not None for p in buf["parts"]):
				jpeg_data = b"".join(buf["parts"])
				del buffers[seq]
				frame = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
				if frame is not None:
					writer, out_path, segment_start, width, height, stop = _recording_loop_body(
						frame,
						buf["ts"],
						buf["lat"],
						buf["lon"],
						buf["alt"],
						timestamps,
						writer,
						out_path,
						segment_start,
						width,
						height,
						output_dir,
						gpx_file,
						"Stream UDP",
					)
					if stop:
						break

			if now - last_clean > 2.0:
				stale = [s for s, b in buffers.items() if now - b["t"] > 2.0]
				for s in stale:
					del buffers[s]
				last_clean = now

	except KeyboardInterrupt:
		pass
	except Exception as e:
		print(f"Error: {e}")
	finally:
		if writer and writer.isOpened():
			writer.release()
		gpx_file.write("  </trkseg></trk>\n</gpx>\n")
		gpx_file.close()
		cv2.destroyAllWindows()
		sock.close()
		print(f"GPX guardado: {gpx_path}")


def main():
	parser = argparse.ArgumentParser(
		description="Receptor video+GPS: tcp (stream confiable) o udp (baja latencia, fragmentado)."
	)
	parser.add_argument(
		"protocol",
		nargs="?",
		default="tcp",
		choices=["tcp", "udp"],
		help="Protocolo (default: tcp)",
	)
	parser.add_argument("--port", type=int, default=5555, help="Puerto (default: 5555)")
	parser.add_argument("--output-dir", type=str, default="./recordings", help="Directorio de grabaciones")
	parser.add_argument("--gpx-dir", type=str, default=".", help="Directorio para archivos GPX")
	args = parser.parse_args()

	if args.protocol == "udp":
		run_udp(args.port, args.output_dir, args.gpx_dir)
	else:
		run_tcp(args.port, args.output_dir, args.gpx_dir)


if __name__ == "__main__":
	main()

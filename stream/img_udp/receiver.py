#!/usr/bin/env python3
"""
Receptor laptop: UDP JPEG fragmentado, session_id en cabecera, solo imágenes (sin VideoWriter ni GPX).
Guarda JPEG re-codificados en recordings/<session>/video_source/ para montaje de vídeo offline.
"""

import argparse
import os
import socket
import struct
import time
from collections import deque

import cv2
import numpy as np

from stream.common import config

HEADER_FMT = config.IMG_UDP_HEADER_FORMAT
HEADER_SIZE = config.IMG_UDP_HEADER_SIZE


def compute_fps(timestamps, window=30):
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


def _draw_overlay(frame, fps, lat, lon, alt, qual):
	cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
	t = f"Lat:{lat:.6f} Lon:{lon:.6f} Alt:{alt:.1f} Q:{qual}"
	cv2.putText(frame, t, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


def run_receiver(
	bind_host,
	port,
	recordings_base,
	save_frames,
	host_jpeg_quality,
	window_title,
):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((bind_host, port))
	print(f"[IMG-UDP] Escuchando en {bind_host}:{port}…")
	print(f"[IMG-UDP] Base recordings: {recordings_base}")
	if save_frames:
		print(f"[IMG-UDP] Guardando frames (calidad host {host_jpeg_quality}) en …/<sesión>/{config.VIDEO_SOURCE_SUBDIR}/")

	timestamps = deque(maxlen=60)
	buffers = {}
	last_clean = time.monotonic()
	current_session = None
	video_source_dir = None
	frame_ix = 0

	try:
		while True:
			try:
				data, _addr = sock.recvfrom(65507)
			except InterruptedError:
				continue

			if len(data) < HEADER_SIZE:
				continue

			meta = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
			seq, total, idx, sess_raw, ts, lat, lon, alt, qual = meta
			payload = data[HEADER_SIZE:]

			if total == 0 or idx >= total:
				continue

			session_id = config.unpack_session_id(sess_raw)
			if not session_id:
				continue

			if session_id != current_session:
				current_session = session_id
				frame_ix = 0
				video_source_dir = os.path.join(
					recordings_base,
					session_id,
					config.VIDEO_SOURCE_SUBDIR,
				)
				if save_frames:
					os.makedirs(video_source_dir, exist_ok=True)
				print(f"[IMG-UDP] Sesión recibida: {session_id} → {video_source_dir}")

			now = time.monotonic()
			if seq not in buffers:
				buffers[seq] = {
					"count": total,
					"parts": [None] * total,
					"ts": ts,
					"lat": lat,
					"lon": lon,
					"alt": alt,
					"qual": qual,
					"t": now,
				}
			buf = buffers[seq]
			buf["ts"] = ts
			buf["lat"] = lat
			buf["lon"] = lon
			buf["alt"] = alt
			buf["qual"] = qual
			buf["t"] = now
			if buf["parts"][idx] is None:
				buf["parts"][idx] = payload

			if all(p is not None for p in buf["parts"]):
				jpeg_data = b"".join(buf["parts"])
				del buffers[seq]
				frame = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
				if frame is not None:
					timestamps.append(buf["ts"])
					fps = compute_fps(timestamps)
					_draw_overlay(frame, fps, buf["lat"], buf["lon"], buf["alt"], int(buf["qual"]))

					if save_frames and video_source_dir:
						encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), int(host_jpeg_quality)]
						ok, buf_jpg = cv2.imencode(".jpg", frame, encode_param)
						if ok:
							out_path = os.path.join(video_source_dir, f"frame_{frame_ix:08d}.jpg")
							frame_ix += 1
							with open(out_path, "wb") as f:
								f.write(buf_jpg.tobytes())

					cv2.imshow(window_title, frame)
					if cv2.waitKey(1) & 0xFF == ord("q"):
						break

			if now - last_clean > 2.0:
				stale = [s for s, b in buffers.items() if now - b["t"] > 2.0]
				for s in stale:
					del buffers[s]
				last_clean = now

	except KeyboardInterrupt:
		pass
	finally:
		cv2.destroyAllWindows()
		sock.close()


def main():
	parser = argparse.ArgumentParser(
		description="Receptor UDP imágenes (JPEG fragmentado; sin grabación de vídeo en vivo)."
	)
	parser.add_argument("--bind", default=os.environ.get("UDP_BIND_HOST", "0.0.0.0"), help="Interfaz bind")
	parser.add_argument("--port", type=int, default=int(os.environ.get("UDP_PORT", "5555")), help="Puerto UDP")
	parser.add_argument(
		"--recordings-base",
		default=os.environ.get("RECORDINGS_DIR", config.RECORDINGS_DIR),
		help="Raíz recordings/ del repo (las imágenes van a <base>/<sesión>/video_source/)",
	)
	parser.add_argument(
		"--no-save-frames",
		action="store_true",
		help="Solo vista previa (no escribe JPEG en disco)",
	)
	parser.add_argument(
		"--host-jpeg-quality",
		type=int,
		default=int(os.environ.get("HOST_SAVE_JPEG_QUALITY", str(config.HOST_SAVE_JPEG_QUALITY))),
		help="Calidad JPEG al guardar en laptop (montaje vídeo)",
	)
	parser.add_argument("--window-title", default="UDP Image Stream", help="Título ventana OpenCV")
	args = parser.parse_args()
	save_frames = config.SAVE_HOST_FRAMES and not args.no_save_frames
	run_receiver(
		args.bind,
		args.port,
		os.path.abspath(args.recordings_base),
		save_frames,
		args.host_jpeg_quality,
		args.window_title,
	)


if __name__ == "__main__":
	main()

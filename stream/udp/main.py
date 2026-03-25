#!/usr/bin/env python3
"""
Cliente UDP de Orange Pi: captura video, lee GPS, envía por UDP (fragmentado).
Reutiliza GPSReader y VideoCapture desde stream.tcp.
"""

import logging
import signal
import sys
import time

import cv2
import numpy as np

from stream.tcp.gps_reader import GPSReader
from stream.tcp.video_capture import VideoCapture

from . import config
from .data_logger import DataLogger
from .udp_sender import UDPSender

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(levelname)s - %(message)s",
	handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def overlay_gps(frame, gps_data):
	if not gps_data:
		return frame
	text = (
		f"Lat: {gps_data['lat']:.6f} Lon: {gps_data['lon']:.6f} "
		f"Alt: {gps_data['alt']:.0f}m Sats: {gps_data['satellites']}"
	)
	cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
	return frame


def main():
	if not config.UDP_HOST:
		logger.error("Define UDP_HOST con la IP de la laptop. Ej: UDP_HOST=192.168.1.50 python -m stream.udp.main")
		sys.exit(1)

	width, height, fps, jpeg_quality = config.get_video_params()
	video = VideoCapture(width, height, fps, jpeg_quality, camera_indices=config.CAMERA_INDICES)
	gps = GPSReader(config.GPS_PORT, config.GPS_BAUD)
	sender = UDPSender(config.UDP_HOST, config.UDP_PORT, config.UDP_PACKET_SIZE)
	data_logger = DataLogger(width, height, float(fps))

	signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
	signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

	gps.start()
	video.start()
	logger.info("Enviando video+GPS por UDP a %s:%d", config.UDP_HOST, config.UDP_PORT)

	try:
		while True:
			item = video.get_frame(timeout=1.0)
			if item is None:
				continue
			jpeg_bytes, timestamp, _frame_number = item
			frame = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
			if frame is None:
				continue

			gps_data = gps.get_data()
			if gps_data:
				frame = overlay_gps(frame, gps_data)
				data_logger.log_gps(gps_data["lat"], gps_data["lon"], gps_data["alt"], timestamp)
			else:
				gps_data = {"lat": 0.0, "lon": 0.0, "alt": 0.0, "quality": 0, "satellites": 0}

			ret, jpeg_with_overlay = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
			if ret:
				jpeg_bytes = jpeg_with_overlay.tobytes()

			sender.send_frame(
				jpeg_bytes,
				timestamp,
				gps_data["lat"],
				gps_data["lon"],
				gps_data["alt"],
				gps_data["quality"],
				gps_data["satellites"],
			)
	except KeyboardInterrupt:
		pass
	finally:
		video.stop()
		gps.stop()
		sender.close()
		data_logger.close()
		logger.info("Cliente UDP detenido")


if __name__ == "__main__":
	main()

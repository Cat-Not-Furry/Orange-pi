#!/usr/bin/env python3
"""
Servidor de streaming con soporte para múltiples cámaras (/dev/video0, video1, ...)
"""

import os
import sys
import socket
import struct
from datetime import datetime

# Parsear --udp, --udp-ip, --udp-port, --record, --record-dir antes de leer config
if __name__ == "__main__":
	import argparse
	_parser = argparse.ArgumentParser()
	_parser.add_argument("--udp", action="store_true", help="Activar envío UDP")
	_parser.add_argument("--udp-ip", type=str, help="IP destino UDP")
	_parser.add_argument("--udp-port", type=int, help="Puerto destino UDP")
	_parser.add_argument("--record", action="store_true", help="Grabar video en alta calidad y máxima resolución")
	_parser.add_argument("--record-dir", type=str, help="Directorio de salida para grabaciones")
	_args, _ = _parser.parse_known_args()
	if _args.udp:
		os.environ.setdefault("UDP_ENABLED", "1")
	if _args.udp_ip:
		os.environ["UDP_TARGET_IP"] = _args.udp_ip
	if _args.udp_port:
		os.environ["UDP_TARGET_PORT"] = str(_args.udp_port)
	if _args.record:
		os.environ.setdefault("RECORD_ENABLED", "1")
	if _args.record_dir:
		os.environ["RECORD_OUTPUT_DIR"] = _args.record_dir

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
import logging
import threading
import time
import psutil
import json
from collections import deque
from flask import Flask, Response, render_template_string

# UDP: fragmentación (frame_id 4B + chunk_idx 2B + total 2B + payload)
_UDP_CHUNK_MAX = 1400
_UDP_HEADER_SIZE = 8

# ===== CONFIGURACIÓN AJUSTABLE =====
# Pueden sobreescribirse con variables de entorno (ej. FRAME_WIDTH=640 pruebas.py)
LOG_FILE = os.environ.get("LOG_FILE", "stream.log")
_cam_str = os.environ.get("CAMERA_INDICES", "0,1,2")
CAMERA_INDICES = [int(x.strip()) for x in _cam_str.split(",") if x.strip()]
PAGE_TITLE = os.environ.get("PAGE_TITLE", "Streaming de video")

# Configuración de logging
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(levelname)s - %(message)s",
	handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", 1280))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", 720))
FPS = int(os.environ.get("FPS", 30))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", 80))  # 0-100
METRICS_LOG_INTERVAL = int(os.environ.get("METRICS_LOG_INTERVAL", 10))
# HTTPS (configuración fuera del código)
HTTPS_PORT = int(os.environ.get("HTTPS_PORT", 5000))
SSL_CRT_FILE = os.environ.get("SSL_CRT_FILE", "")
SSL_KEY_FILE = os.environ.get("SSL_KEY_FILE", "")
SSL_ADHOC = os.environ.get("SSL_ADHOC", "0") == "1"
# Estabilización y optimización
FRAME_BUFFER_SIZE = int(os.environ.get("FRAME_BUFFER_SIZE", 0))  # 0 = desactivado
UNSTABLE_NETWORK_MODE = os.environ.get("UNSTABLE_NETWORK_MODE", "0") == "1"
LONG_RANGE_MODE = os.environ.get("LONG_RANGE_MODE", "0") == "1"
CPU_INTENSIVE_MODE = os.environ.get("CPU_INTENSIVE_MODE", "0") == "1"
# Recursos dinámicos y UDP
DYNAMIC_RESOURCES = os.environ.get("DYNAMIC_RESOURCES", "0") == "1"
UDP_ENABLED = os.environ.get("UDP_ENABLED", "0") == "1"
UDP_TARGET_IP = os.environ.get("UDP_TARGET_IP", "127.0.0.1")
UDP_TARGET_PORT = int(os.environ.get("UDP_TARGET_PORT", 5005))
# Grabación en alta calidad
RECORD_ENABLED = os.environ.get("RECORD_ENABLED", "0") == "1"
RECORD_OUTPUT_DIR = os.environ.get("RECORD_OUTPUT_DIR", "./recordings")
RECORD_WIDTH = int(os.environ.get("RECORD_WIDTH", 1920))
RECORD_HEIGHT = int(os.environ.get("RECORD_HEIGHT", 1080))
RECORD_QUALITY = int(os.environ.get("RECORD_QUALITY", 95))
RECORD_USE_CAMERA_NATIVE = os.environ.get("RECORD_USE_CAMERA_NATIVE", "0") == "1"
# 60 FPS estable
FPS_60_MODE = os.environ.get("FPS_60_MODE", "0") == "1"
# ===================================

# Aplicar overrides de modo (después de leer variables base)
if FPS_60_MODE:
	FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
	FPS = 60
	JPEG_QUALITY = 80
elif LONG_RANGE_MODE:
	FRAME_WIDTH, FRAME_HEIGHT = 640, 360
	FPS = 15
	JPEG_QUALITY = 60
elif UNSTABLE_NETWORK_MODE:
	FRAME_WIDTH = min(FRAME_WIDTH, 854)
	FRAME_HEIGHT = min(FRAME_HEIGHT, 480)
	FPS = min(FPS, 20)
	JPEG_QUALITY = min(JPEG_QUALITY, 65)

if CPU_INTENSIVE_MODE:
	JPEG_QUALITY = max(JPEG_QUALITY, 90)

if RECORD_ENABLED:
	if RECORD_USE_CAMERA_NATIVE:
		FRAME_WIDTH = 3840
		FRAME_HEIGHT = 2160
	else:
		FRAME_WIDTH = RECORD_WIDTH
		FRAME_HEIGHT = RECORD_HEIGHT

# Variables globales
camera = None
camera_index = None
frame_count = 0
bytes_sent = 0
start_time = time.time()
stats = {"fps": 0, "cpu": 0, "mem": 0, "uptime": 0, "camera": "Ninguna", "bandwidth_mbps": 0}
frame_buffer = None
resource_limiter = None
video_writer = None
dynamic_params = {"fps": FPS, "jpeg_quality": JPEG_QUALITY, "width": FRAME_WIDTH, "height": FRAME_HEIGHT}


class FrameBuffer:
	"""Cola circular de frames JPEG para clientes. Thread-safe."""

	def __init__(self, maxlen: int):
		self._deque = deque(maxlen=maxlen)
		self._lock = threading.Lock()

	def put(self, frame_bytes: bytes) -> None:
		with self._lock:
			self._deque.append(frame_bytes)

	def get_latest(self):
		"""Devuelve el último frame o None si el buffer está vacío."""
		with self._lock:
			return self._deque[-1] if self._deque else None


def _get_current_fps():
	"""FPS efectivo (dinámico o fijo)."""
	return dynamic_params["fps"] if DYNAMIC_RESOURCES and resource_limiter else FPS


def _get_current_jpeg_quality():
	"""Calidad JPEG efectiva (dinámica o fija)."""
	return dynamic_params["jpeg_quality"] if DYNAMIC_RESOURCES and resource_limiter else JPEG_QUALITY


def _udp_fragment_and_send(sock, target: tuple, frame_bytes: bytes, frame_id: int) -> int:
	"""Fragmenta y envía un frame por UDP."""
	payload_size = _UDP_CHUNK_MAX - _UDP_HEADER_SIZE
	total = (len(frame_bytes) + payload_size - 1) // payload_size
	sent = 0
	for idx in range(total):
		offset = idx * payload_size
		chunk_data = frame_bytes[offset : offset + payload_size]
		header = struct.pack(">IHH", frame_id, idx, total)
		try:
			sock.sendto(header + chunk_data, target)
			sent += len(header) + len(chunk_data)
		except OSError as e:
			logger.warning(f"UDP send: {e}")
			break
	return sent


def _udp_send_loop(frame_getter, target_ip: str, target_port: int, fps: float) -> None:
	"""Hilo que envía frames por UDP."""
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# Buffer de salida mayor para reducir pérdida en redes de largo alcance
	try:
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
	except OSError:
		pass
	target = (target_ip, target_port)
	frame_id = 0
	interval = 1.0 / fps if fps > 0 else 0.033
	next_send = time.perf_counter()
	while True:
		frame_bytes = frame_getter()
		if frame_bytes:
			_udp_fragment_and_send(sock, target, frame_bytes, frame_id)
			frame_id = (frame_id + 1) & 0xFFFFFFFF
		next_send += interval
		now = time.perf_counter()
		if next_send < now:
			next_send = now + interval
		time.sleep(max(0, next_send - now))


def _init_video_writer(width: int, height: int, fps: float):
	"""Crea VideoWriter para grabación. Prueba H264, MP4V, MJPEG. Aplica RECORD_QUALITY si el backend lo soporta."""
	os.makedirs(RECORD_OUTPUT_DIR, exist_ok=True)
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	codecs = [
		("avc1", ".mp4"),
		("H264", ".mp4"),
		("mp4v", ".mp4"),
		("MJPG", ".avi"),
	]
	quality_prop = getattr(cv2, "VIDEOWRITER_PROP_QUALITY", 1)
	for fourcc_str, ext in codecs:
		path = os.path.join(RECORD_OUTPUT_DIR, f"recording_{timestamp}{ext}")
		fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
		writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
		if writer.isOpened():
			try:
				writer.set(quality_prop, RECORD_QUALITY)
			except Exception:
				pass
			logger.info(f"Grabación activa: {path} ({fourcc_str}, {width}x{height} @ {fps}fps, calidad={RECORD_QUALITY})")
			return writer
		writer.release()
	logger.error("No se pudo inicializar ningún códec de video para grabación")
	return None


def _write_frame_if_recording(frame):
	"""Escribe frame en video_writer si la grabación está activa."""
	global video_writer
	if video_writer and video_writer.isOpened():
		video_writer.write(frame)


def _process_frame(frame):
	"""Aplica procesamiento opcional para aumentar CPU."""
	if CPU_INTENSIVE_MODE:
		h, w = frame.shape[:2]
		frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LANCZOS4)
		frame = cv2.GaussianBlur(frame, (3, 3), 0)
	return frame


def _camera_capture_loop():
	"""Hilo que captura frames y los pone en el buffer."""
	global frame_count, frame_buffer
	next_frame_time = time.perf_counter()
	while camera and camera.isOpened():
		success, frame = camera.read()
		if not success:
			time.sleep(0.1)
			continue
		frame_count += 1
		frame = _process_frame(frame)
		_write_frame_if_recording(frame)
		jpeg_q = _get_current_jpeg_quality()
		encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_q]
		ret, buffer = cv2.imencode(".jpg", frame, encode_param)
		if ret and frame_buffer:
			frame_buffer.put(buffer.tobytes())
		fps = _get_current_fps()
		interval = 1.0 / fps if fps > 0 else 0.033
		next_frame_time += interval
		now = time.perf_counter()
		if next_frame_time < now:
			next_frame_time = now + interval
		time.sleep(max(0, next_frame_time - now))


def find_camera():
    """Prueba varios índices hasta encontrar una cámara accesible"""
    for idx in CAMERA_INDICES:
        logger.info(f"Probando cámara con índice {idx} (/dev/video{idx})...")
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            # Verificar que realmente puede leer un frame
            ret, _ = cap.read()
            if ret:
                logger.info(f"✅ Cámara encontrada en /dev/video{idx}")
                cap.release()
                return idx
            else:
                logger.warning(f"Índice {idx} se abrió pero no entrega frames")
        cap.release()
    logger.error("❌ No se encontró ninguna cámara en los índices probados")
    return None


def init_camera(index):
    """Inicializa la cámara con configuración óptima"""
    global camera
    camera = cv2.VideoCapture(index)

    # Intentar configurar con códec MJPEG si es posible (menor CPU)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, FPS)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reducir buffer para baja latencia

    # Verificar configuración real
    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = camera.get(cv2.CAP_PROP_FPS)

    logger.info(
        f"Cámara /dev/video{index} inicializada: {actual_width}x{actual_height} @ {actual_fps}fps"
    )

    if actual_width != FRAME_WIDTH:
        logger.warning(
            f"Resolución solicitada {FRAME_WIDTH}x{FRAME_HEIGHT} no soportada, usando {actual_width}x{actual_height}"
        )

    stats["camera"] = f"/dev/video{index}"
    return camera.isOpened()


def monitor_system():
    """Hilo para monitorear recursos del sistema"""
    global stats
    last_metrics_log = 0
    while True:
        stats["cpu"] = psutil.cpu_percent()
        stats["mem"] = psutil.virtual_memory().percent
        stats["uptime"] = time.time() - start_time
        stats["fps"] = frame_count / stats["uptime"] if stats["uptime"] > 0 else 0
        stats["bandwidth_mbps"] = (bytes_sent * 8 / 1_000_000) / stats["uptime"] if stats["uptime"] > 0 else 0

        now = int(time.time())
        if now - last_metrics_log >= METRICS_LOG_INTERVAL:
            last_metrics_log = now
            logger.info(
                f"MÉTRICAS: FPS={stats['fps']:.1f}, CPU={stats['cpu']}%, Mem={stats['mem']}%, "
                f"BW={stats['bandwidth_mbps']:.2f} Mbps, Cámara={stats['camera']}"
            )
        time.sleep(2)


def _make_mjpeg_chunk(frame_bytes: bytes) -> bytes:
	"""Construye chunk MJPEG con Content-Length para mejor parsing en cliente."""
	header = (
		b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
		+ str(len(frame_bytes)).encode()
		+ b"\r\n\r\n"
	)
	return header + frame_bytes + b"\r\n"


def generate_frames():
	"""Generador de frames para streaming."""
	global frame_count, bytes_sent

	if not camera or not camera.isOpened():
		logger.error("Cámara no disponible")
		return

	next_frame_time = time.perf_counter()

	if frame_buffer:
		# Modo buffer: leer desde buffer
		while True:
			frame_bytes = frame_buffer.get_latest()
			if frame_bytes:
				now = time.perf_counter()
				if now >= next_frame_time:
					chunk = _make_mjpeg_chunk(frame_bytes)
					bytes_sent += len(chunk)
					yield chunk
					fps = _get_current_fps()
					interval = 1.0 / fps if fps > 0 else 0.033
					next_frame_time += interval
					if next_frame_time < now:
						next_frame_time = now + interval
			time.sleep(0.001)
	else:
		# Modo directo: leer de cámara
		while True:
			success, frame = camera.read()
			if not success:
				logger.error("Error capturando frame")
				break
			frame_count += 1
			frame = _process_frame(frame)
			_write_frame_if_recording(frame)
			jpeg_q = _get_current_jpeg_quality()
			encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_q]
			ret, buffer = cv2.imencode(".jpg", frame, encode_param)
			frame_bytes = buffer.tobytes()
			now = time.perf_counter()
			if now >= next_frame_time:
				chunk = _make_mjpeg_chunk(frame_bytes)
				bytes_sent += len(chunk)
				yield chunk
				fps = _get_current_fps()
				interval = 1.0 / fps if fps > 0 else 0.033
				next_frame_time += interval
				if next_frame_time < now:
					next_frame_time = now + interval
			time.sleep(max(0, next_frame_time - time.perf_counter()))


@app.route("/video_feed")
def video_feed():
    logger.info("Cliente conectado al feed de video")
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/stats")
def get_stats():
    """Endpoint para ver estadísticas en tiempo real"""
    return json.dumps(stats)


@app.route("/")
def index():
	return render_template_string(
		"""
	<!DOCTYPE html>
	<html>
	<head>
		<title>{{ page_title }}</title>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<style>
			body { font-family: Arial; text-align: center; background: #1a1a1a; color: white; }
			img { max-width: 100%; border: 2px solid #444; }
			#stats { margin: 20px; padding: 10px; background: #333; border-radius: 5px; display: inline-block; }
		</style>
	</head>
	<body>
		<h1>Streaming de video</h1>
		<img id="video_feed" src="{{ url_for('video_feed') }}" width="{{ frame_width }}" height="{{ frame_height }}" alt="Video stream">
        
        <div id="stats">
            <h3>Estadísticas</h3>
            <p>Cámara: <span id="cam">{{ stats.camera }}</span></p>
            <p>FPS: <span id="fps">0</span></p>
            <p>CPU: <span id="cpu">0</span>%</p>
            <p>Memoria: <span id="mem">0</span>%</p>
            <p>Ancho de banda: <span id="bw">0</span> Mbps</p>
            <p>Tiempo activo: <span id="uptime">0</span>s</p>
        </div>

        <script>
            let statsFailCount = 0;
            const MAX_STATS_FAILS = 3;

            function updateStats() {
                fetch('/stats')
                    .then(response => response.json())
                    .then(data => {
                        statsFailCount = 0;
                        document.getElementById('fps').textContent = data.fps.toFixed(1);
                        document.getElementById('cpu').textContent = data.cpu;
                        document.getElementById('mem').textContent = data.mem;
                        document.getElementById('bw').textContent = (data.bandwidth_mbps || 0).toFixed(2);
                        document.getElementById('uptime').textContent = Math.floor(data.uptime);
                    })
                    .catch(() => {
                        statsFailCount++;
                        if (statsFailCount >= MAX_STATS_FAILS) {
                            const img = document.getElementById('video_feed');
                            img.src = img.src.split('?')[0] + '?t=' + Date.now();
                            statsFailCount = 0;
                        }
                    });
            }
            setInterval(updateStats, 2000);
        </script>
    </body>
	</html>
	""",
		stats=stats,
		page_title=PAGE_TITLE,
		frame_width=FRAME_WIDTH,
		frame_height=FRAME_HEIGHT,
	)


if __name__ == "__main__":
	logger.info("Iniciando servidor de streaming...")

	try:
		import psutil
	except ImportError:
		logger.error("psutil no instalado. Ejecuta: pip install psutil")
		exit(1)

	cam_idx = find_camera()
	if cam_idx is None:
		logger.error("No se pudo encontrar ninguna cámara. Abortando.")
		exit(1)

	if not init_camera(cam_idx):
		logger.error("No se pudo inicializar la cámara")
		exit(1)

	if RECORD_ENABLED:
		actual_w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
		actual_h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
		actual_fps = camera.get(cv2.CAP_PROP_FPS) or FPS
		video_writer = _init_video_writer(actual_w, actual_h, actual_fps)

	if FRAME_BUFFER_SIZE > 0 or UDP_ENABLED:
		if FRAME_BUFFER_SIZE <= 0 and UDP_ENABLED:
			frame_buffer = FrameBuffer(maxlen=5)
			logger.info("Buffer activo para UDP (5 frames)")
		else:
			frame_buffer = FrameBuffer(maxlen=FRAME_BUFFER_SIZE)
		camera_thread = threading.Thread(target=_camera_capture_loop, daemon=True)
		camera_thread.start()
		buf_size = FRAME_BUFFER_SIZE if FRAME_BUFFER_SIZE > 0 else 5
		logger.info(f"Buffer de frames activo: {buf_size} frames")

	if DYNAMIC_RESOURCES:
		try:
			from resource_limiter import ResourceLimiter
		except ImportError:
			from stream.resource_limiter import ResourceLimiter
		initial_level = 7 if FPS_60_MODE else int(os.environ.get("RESOURCE_INITIAL_LEVEL", 4))
		initial_level = max(0, min(initial_level, 8))
		resource_limiter = ResourceLimiter(
			cpu_target=float(os.environ.get("CPU_TARGET_PCT", 70)),
			ram_target=float(os.environ.get("RAM_TARGET_PCT", 70)),
			target_fps=int(os.environ.get("TARGET_FPS", 60)),
			initial_level=initial_level,
		)
		dynamic_params.update(resource_limiter.get_recommended_params())

		def _on_params_updated(params):
			dynamic_params.update(params)

		resource_limiter.start_adaptation_loop(_on_params_updated)
		logger.info("Modo dinámico de recursos activo")

	if UDP_ENABLED and frame_buffer:
		def _udp_frame_getter():
			return frame_buffer.get_latest() if frame_buffer else None

		udp_fps = _get_current_fps() if (DYNAMIC_RESOURCES and resource_limiter) else FPS
		udp_thread = threading.Thread(
			target=_udp_send_loop,
			args=(_udp_frame_getter, UDP_TARGET_IP, UDP_TARGET_PORT, udp_fps),
			daemon=True,
		)
		udp_thread.start()
		logger.info(f"UDP activo: {UDP_TARGET_IP}:{UDP_TARGET_PORT}")

	monitor_thread = threading.Thread(target=monitor_system, daemon=True)
	monitor_thread.start()

	ssl_context = None
	if SSL_ADHOC:
		ssl_context = "adhoc"
		logger.info("HTTPS activo (certificado adhoc, solo desarrollo)")
	elif SSL_CRT_FILE and SSL_KEY_FILE and os.path.isfile(SSL_CRT_FILE) and os.path.isfile(SSL_KEY_FILE):
		ssl_context = (SSL_CRT_FILE, SSL_KEY_FILE)
		logger.info(f"HTTPS activo con certificados: {SSL_CRT_FILE}")
	elif SSL_CRT_FILE or SSL_KEY_FILE:
		logger.warning("SSL_CRT_FILE/SSL_KEY_FILE definidos pero archivos no encontrados. Usando HTTP.")

	try:
		app.run(host="0.0.0.0", port=HTTPS_PORT, debug=False, threaded=True, ssl_context=ssl_context)
	except KeyboardInterrupt:
		logger.info("Servidor detenido por el usuario")
	finally:
		if camera:
			camera.release()
		if video_writer and video_writer.isOpened():
			video_writer.release()
			logger.info("Grabación finalizada")
		logger.info("Recursos liberados")

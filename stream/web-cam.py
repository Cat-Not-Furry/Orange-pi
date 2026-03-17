#!/usr/bin/env python3
"""
Servidor de streaming con soporte para múltiples cámaras (/dev/video0, video1, ...)
"""

import os
import cv2
import logging
import threading
import time
import psutil
import json
from flask import Flask, Response, render_template_string

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("stream.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== CONFIGURACIÓN AJUSTABLE =====
# Pueden sobreescribirse con variables de entorno (ej. FRAME_WIDTH=640 pruebas.py)
CAMERA_INDICES = [0, 1, 2]  # /dev/video0, video1, video2
FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", 1280))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", 720))
FPS = int(os.environ.get("FPS", 30))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", 80))  # 0-100
METRICS_LOG_INTERVAL = int(os.environ.get("METRICS_LOG_INTERVAL", 10))
# ===================================

# Variables globales
camera = None
camera_index = None
frame_count = 0
bytes_sent = 0
start_time = time.time()
stats = {"fps": 0, "cpu": 0, "mem": 0, "uptime": 0, "camera": "Ninguna", "bandwidth_mbps": 0}


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


def generate_frames():
    """Generador de frames para streaming"""
    global frame_count, bytes_sent

    if not camera or not camera.isOpened():
        logger.error("Cámara no disponible")
        return

    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
    while True:
        success, frame = camera.read()
        if not success:
            logger.error("Error capturando frame")
            break

        frame_count += 1
        ret, buffer = cv2.imencode(".jpg", frame, encode_param)
        frame_bytes = buffer.tobytes()
        chunk = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        bytes_sent += len(chunk)

        yield chunk

        time.sleep(1 / FPS)


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
        <title>Streaming desde Orange Pi</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial; text-align: center; background: #1a1a1a; color: white; }
            img { max-width: 100%; border: 2px solid #444; }
            #stats { margin: 20px; padding: 10px; background: #333; border-radius: 5px; display: inline-block; }
        </style>
    </head>
    <body>
        <h1>📡 Video desde el dron</h1>
        <img src="{{ url_for('video_feed') }}" width="1280" height="720">
        
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
            function updateStats() {
                fetch('/stats')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('fps').textContent = data.fps.toFixed(1);
                        document.getElementById('cpu').textContent = data.cpu;
                        document.getElementById('mem').textContent = data.mem;
                        document.getElementById('bw').textContent = (data.bandwidth_mbps || 0).toFixed(2);
                        document.getElementById('uptime').textContent = Math.floor(data.uptime);
                    });
            }
            setInterval(updateStats, 2000);
        </script>
    </body>
    </html>
    """,
        stats=stats,
    )


if __name__ == "__main__":
    logger.info("Iniciando servidor de streaming...")

    # Verificar dependencias
    try:
        import psutil
    except ImportError:
        logger.error("psutil no instalado. Ejecuta: pip install psutil")
        exit(1)

    # Buscar cámara disponible
    cam_idx = find_camera()
    if cam_idx is None:
        logger.error("No se pudo encontrar ninguna cámara. Abortando.")
        exit(1)

    # Inicializar cámara encontrada
    if not init_camera(cam_idx):
        logger.error("No se pudo inicializar la cámara")
        exit(1)

    # Iniciar monitor de sistema en segundo plano
    monitor_thread = threading.Thread(target=monitor_system, daemon=True)
    monitor_thread.start()

    # Ejecutar servidor
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    finally:
        if camera:
            camera.release()
        logger.info("Recursos liberados")

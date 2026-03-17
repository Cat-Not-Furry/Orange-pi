#!/usr/bin/env python3
"""
Servidor de streaming con logging y optimizaciones para red WiFi
"""

import cv2
import logging
import threading
import time
import psutil
import json
from flask import Flask, Response, render_template_string
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("stream.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de la cámara
CAMERA_INDEX = 0
FRAME_WIDTH = 1280  # HD
FRAME_HEIGHT = 720  # 720p
FPS = 30
BITRATE = 2000  # kbps (ajusta según tu red)

# Variables globales
camera = None
frame_count = 0
start_time = time.time()
stats = {"fps": 0, "cpu": 0, "mem": 0, "uptime": 0}


def init_camera():
    """Inicializa la cámara con configuración óptima"""
    global camera
    camera = cv2.VideoCapture(CAMERA_INDEX)

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
        f"Cámara inicializada: {actual_width}x{actual_height} @ {actual_fps}fps"
    )

    if actual_width != FRAME_WIDTH:
        logger.warning(
            f"Resolución solicitada {FRAME_WIDTH}x{FRAME_HEIGHT} no soportada, usando {actual_width}x{actual_height}"
        )

    return camera.isOpened()


def monitor_system():
    """Hilo para monitorear recursos del sistema"""
    global stats
    while True:
        stats["cpu"] = psutil.cpu_percent()
        stats["mem"] = psutil.virtual_memory().percent
        stats["uptime"] = time.time() - start_time
        stats["fps"] = frame_count / stats["uptime"] if stats["uptime"] > 0 else 0
        time.sleep(2)


def generate_frames():
    """Generador de frames para streaming"""
    global frame_count

    if not camera or not camera.isOpened():
        logger.error("Cámara no disponible")
        return

    while True:
        success, frame = camera.read()
        if not success:
            logger.error("Error capturando frame")
            break

        frame_count += 1

        # Opcional: Reducir calidad para ajustar bitrate
        # encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # 80% calidad
        # ret, buffer = cv2.imencode('.jpg', frame, encode_param)

        ret, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

        # Pequeña pausa para controlar FPS
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
    return render_template_string("""
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
            <p>FPS: <span id="fps">0</span></p>
            <p>CPU: <span id="cpu">0</span>%</p>
            <p>Memoria: <span id="mem">0</span>%</p>
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
                        document.getElementById('uptime').textContent = Math.floor(data.uptime);
                    });
            }
            setInterval(updateStats, 2000);
        </script>
    </body>
    </html>
    """)


if __name__ == "__main__":
    logger.info("Iniciando servidor de streaming...")

    # Verificar dependencias
    try:
        import psutil
    except ImportError:
        logger.error("psutil no instalado. Ejecuta: pip install psutil")
        exit(1)

    # Inicializar cámara
    if not init_camera():
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

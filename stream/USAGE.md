# Stream: instrucciones de uso

Streaming de video y GPS desde Orange Pi hacia laptop. El código está separado por dispositivo.

## Separación por dispositivo

| Ubicación | Dispositivo | Función |
|-----------|-------------|---------|
| **stream/** (raíz) | Laptop (host) | Recibe, muestra y graba video |
| **stream/tcp/** | Orange Pi (tarjeta) | Captura, transmite video y GPS |

## Estructura de directorios

```
stream/
├── recorder.py          # Laptop: recibe HTTP, graba
├── receiver.py          # Laptop: recibe TCP, graba + GPX
├── USAGE.md
├── .env.example
└── tcp/
    ├── web-cam.py       # Orange Pi: servidor HTTP
    ├── menu.py          # Orange Pi: menú de modos
    ├── main.py          # Orange Pi: cliente TCP
    ├── gps_reader.py
    ├── video_capture.py
    ├── tcp_sender.py
    ├── data_logger.py
    ├── resource_limiter.py
    └── pruebas.py
```

## Requisitos

- Python 3
- Dependencias: `opencv-python`, `psutil`, `flask`, `pyopenssl` (solo HTTPS adhoc), `pynmea2`, `pyserial`

```bash
pip install -r ../requirements.txt
```

## Requisitos de red

El proyecto **no requiere conexión a internet**. Solo necesita que el dispositivo (Orange Pi) y la laptop estén en la misma red local:

```
[Laptop] <--WiFi/Ethernet--> [Router/AP] <--WiFi/Ethernet--> [Orange Pi]
```

---

## Modo HTTP

Transmisión MJPEG por HTTP. Usa `web-cam.py` en Orange Pi y `recorder.py` en laptop.

### En Orange Pi

```bash
cd stream/tcp
python menu.py
# o directamente:
python web-cam.py
```

Por defecto: HTTP en puerto 5000, 1280x720, 30 fps, JPEG 80. Abre en navegador: `http://<IP_ORANGE_PI>:5000`

### En laptop

```bash
cd stream
python recorder.py --host IP_ORANGE_PI --port 5000
python recorder.py --url http://192.168.1.100:5000/video_feed --output-dir ./recordings
```

- Reintenta la conexión hasta que el Orange Pi esté disponible
- Guarda en `./recordings/recording_YYYYMMDD_HHMMSS.mp4` (o `.avi`)
- Ctrl+C para detener

---

## Modo TCP

Transmisión por TCP con video + GPS. Usa `main.py` en Orange Pi y `receiver.py` en laptop.

### En laptop (primero)

```bash
cd stream
python receiver.py
```

Espera en puerto 5555 (configurable). Muestra video en tiempo real, graba en segmentos y exporta GPX.

### En Orange Pi

```bash
cd stream/tcp
python menu.py
# o desde la raíz del proyecto:
TCP_HOST=192.168.1.50 python -m stream.tcp.main
```

Configura `TCP_HOST` con la IP de la laptop (ej. 192.168.1.50).

### Salidas

- **Video**: `stream/recordings/` (segmentos de 60s)
- **GPX**: `trayectoria_YYYYMMDD_HHMMSS.gpx`

---

## Menú unificado (Orange Pi)

En `stream/tcp/` ejecuta `python menu.py` para elegir:

1. TCP Calidad máxima/superior (1920x1080 60fps o 1280x720 60fps)
2. TCP Calidad normal (640x360 30fps)
3. HTTP Máxima calidad (1920x1080 60fps)

---

## Variables de entorno

### HTTP (web-cam.py)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `CAMERA_INDICES` | 0,1,2 | Índices de cámara a probar |
| `LOG_FILE` | stream.log | Archivo de log |
| `FRAME_WIDTH` | 1280 | Ancho de frame |
| `FRAME_HEIGHT` | 720 | Alto de frame |
| `FPS` | 30 | Frames por segundo |
| `JPEG_QUALITY` | 80 | Calidad JPEG (0-100) |
| `HTTPS_PORT` | 5000 | Puerto del servidor |
| `MAX_QUALITY_MODE` | 0 | 1 = 1920x1080, 60fps, JPEG 95 |
| `LONG_RANGE_MODE` | 0 | 1 = 640x360, 15fps (alcance 80m) |
| `UNSTABLE_NETWORK_MODE` | 0 | 1 = menor resolución para red inestable |
| `DYNAMIC_RESOURCES` | 0 | 1 = ajuste dinámico CPU/RAM ~70% |
| `SSL_CRT_FILE`, `SSL_KEY_FILE` | - | Certificados HTTPS |
| `SSL_ADHOC` | 0 | 1 = HTTPS con certificado autofirmado |

### TCP (main.py)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TCP_HOST` | - | IP de la laptop (obligatorio) |
| `TCP_PORT` | 5555 | Puerto del receptor |
| `GPS_PORT` | /dev/ttyS3 | Puerto serie del GPS |
| `TCP_QUALITY_MAX` | 0 | 1 = 1920x1080 60fps JPEG95 |
| `TCP_QUALITY_SUPERIOR` | 0 | 1 = 1280x720 60fps JPEG90 |
| `TCP_QUALITY_NORMAL` | 0 | 1 = 640x360 30fps JPEG70 |

---

## Comandos rápidos

### Orange Pi

```bash
cd stream/tcp
python menu.py
python web-cam.py
python main.py
```

### Laptop

```bash
cd stream
python receiver.py
python recorder.py --host IP_ORANGE_PI --port 5000
```

---

## Endpoints HTTP (web-cam)

| Ruta | Descripción |
|------|-------------|
| `/` | Página con stream y estadísticas |
| `/video_feed` | Stream MJPEG (para `<img src="">` o VLC) |
| `/stats` | JSON con FPS, CPU, memoria, ancho de banda |

## Logs

- Consola: métricas cada 10 segundos
- Archivo: `stream.log` por defecto (configurable con `LOG_FILE`)

## Detener

Ctrl+C para detener el servidor y liberar la cámara.

# Instrucciones de uso: web-cam.py

Servidor de streaming de video desde cámara USB (compatible con Orange Pi y Raspberry Pi).

## Requisitos

- Python 3
- Dependencias: `opencv-python`, `psutil`, `flask`, `pyopenssl` (solo para HTTPS adhoc)

```bash
pip install -r ../requirements.txt
```

## Requisitos de red (solo conexión a host)

El proyecto **no requiere conexión a internet**. Solo necesita que el dispositivo (Orange Pi, Raspberry Pi) y el cliente (laptop) estén en la misma red local:

```
[Laptop] <--WiFi/Ethernet--> [Router/AP] <--WiFi/Ethernet--> [Orange Pi / Raspberry Pi]
```

El router no necesita estar conectado a internet (WAN). La transmisión es exclusivamente entre dispositivos en la red local.

## Inicio básico

```bash
cd stream
python web-cam.py
```

Por defecto: HTTP en puerto 5000, resolución 1280x720, 30 fps, calidad JPEG 80.

Abre en el navegador: `http://<IP_ORANGE_PI>:5000`

## Configuración

El servidor se configura mediante variables de entorno. No hay opciones de línea de comandos para web-cam.py.

## Variables de entorno

Configuración sin modificar código:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `CAMERA_INDICES` | 0,1,2 | Índices de cámara a probar (/dev/video0, etc.) |
| `LOG_FILE` | stream.log | Archivo de log |
| `PAGE_TITLE` | Streaming de video | Título de la página web |
| `FRAME_WIDTH` | 1280 | Ancho de frame |
| `FRAME_HEIGHT` | 720 | Alto de frame |
| `FPS` | 30 | Frames por segundo |
| `JPEG_QUALITY` | 80 | Calidad JPEG (0-100) |
| `HTTPS_PORT` | 5000 | Puerto del servidor |
| `FRAME_BUFFER_SIZE` | 0 | Buffer de frames (0=desactivado) |
| `LONG_RANGE_MODE` | 0 | 1 = 640x360, 15fps (alcance 80m) |
| `UNSTABLE_NETWORK_MODE` | 0 | 1 = menor resolución para red inestable |
| `MAX_QUALITY_MODE` | 0 | 1 = 1920x1080, 60fps, JPEG 95 (óptimo para grabación) |
| `FPS_60_MODE` | 0 | 1 = 1280x720 a 60 fps estable |
| `DYNAMIC_RESOURCES` | 0 | 1 = ajuste dinámico CPU/RAM ~70% |
| `RESOURCE_INITIAL_LEVEL` | 4 | Nivel inicial (0-8) para recursos dinámicos |
| `SSL_CRT_FILE` | - | Ruta certificado HTTPS |
| `SSL_KEY_FILE` | - | Ruta clave privada HTTPS |
| `SSL_ADHOC` | 0 | 1 = HTTPS con certificado autofirmado |

### Ejemplos con variables

```bash
# Alcance largo (80m)
LONG_RANGE_MODE=1 python web-cam.py

# Red inestable + buffer
UNSTABLE_NETWORK_MODE=1 FRAME_BUFFER_SIZE=8 python web-cam.py

# Recursos dinámicos (CPU ~70%)
DYNAMIC_RESOURCES=1 python web-cam.py

# Máxima calidad (para grabación en laptop)
MAX_QUALITY_MODE=1 python web-cam.py

# 60 FPS estable
FPS_60_MODE=1 python web-cam.py

# HTTPS con certificados
SSL_CRT_FILE=cert.pem SSL_KEY_FILE=key.pem python web-cam.py

# HTTPS adhoc (desarrollo)
SSL_ADHOC=1 python web-cam.py
```

## Modos predefinidos (menú)

Ejecuta `python menu.py` para acceder a modos sin escribir variables:

1. Máxima calidad (1920x1080, 60fps) - para grabación en laptop
2. Alcance largo 80m (640x360, 15fps)
3. Red inestable (buffer + menor calidad)
4. 60 FPS estable (1280x720)
5. Recursos dinámicos (CPU/RAM ~70%)
6. HTTPS (certificado adhoc)

Para grabar en laptop: `python recorder.py --host IP_ORANGE_PI --port 5000`

## Endpoints HTTP

| Ruta | Descripción |
|------|-------------|
| `/` | Página con stream y estadísticas |
| `/video_feed` | Stream MJPEG (para `<img src="">` o VLC) |
| `/stats` | JSON con FPS, CPU, memoria, ancho de banda |

## Grabación en laptop

La grabación se hace en la laptop, no en el Orange Pi. Ejecuta `recorder.py` en la laptop:

```bash
# En la laptop (conectada a la misma red que el Orange Pi)
python recorder.py --host 192.168.1.100 --port 5000
python recorder.py --url http://192.168.1.100:5000/video_feed --output-dir ./videos
```

- Reintenta la conexión hasta que el Orange Pi esté disponible
- Guarda en `./recordings/recording_YYYYMMDD_HHMMSS.mp4` (o `.avi`)
- Ctrl+C para detener la grabación

En el Orange Pi, usa el modo "Máxima calidad" para mejor resultado.

## Logs

- Consola: métricas cada 10 segundos (FPS, CPU, memoria, ancho de banda)
- Archivo: `stream.log` por defecto (configurable con `LOG_FILE`)

## Detener

Ctrl+C para detener el servidor y liberar la cámara.

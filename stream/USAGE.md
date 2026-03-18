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

## Opciones de línea de comandos

| Opción | Descripción |
|--------|-------------|
| `--udp` | Activar envío de video por UDP |
| `--udp-ip IP` | IP destino para UDP (default: 127.0.0.1) |
| `--udp-port PUERTO` | Puerto destino UDP (default: 5005) |
| `--record` | Grabar video en alta calidad y máxima resolución |
| `--record-dir RUTA` | Directorio de salida para grabaciones |

### Ejemplos

```bash
# Modo normal
python web-cam.py

# Transmitir por UDP a otro equipo
python web-cam.py --udp --udp-ip 192.168.1.50 --udp-port 5005

# Grabar mientras transmite
python web-cam.py --record

# Grabar en directorio específico
python web-cam.py --record --record-dir /home/pi/videos

# Combinar UDP y grabación
python web-cam.py --udp --udp-ip 192.168.1.50 --record
```

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
| `FPS_60_MODE` | 0 | 1 = 1280x720 a 60 fps estable |
| `DYNAMIC_RESOURCES` | 0 | 1 = ajuste dinámico CPU/RAM ~70% |
| `RESOURCE_INITIAL_LEVEL` | 4 | Nivel inicial (0-8) para recursos dinámicos |
| `UDP_ENABLED` | 0 | 1 = envío UDP activo |
| `UDP_TARGET_IP` | 127.0.0.1 | IP destino UDP |
| `UDP_TARGET_PORT` | 5005 | Puerto destino UDP |
| `RECORD_ENABLED` | 0 | 1 = grabación activa |
| `RECORD_WIDTH` | 1920 | Ancho para grabación |
| `RECORD_HEIGHT` | 1080 | Alto para grabación |
| `RECORD_QUALITY` | 95 | Calidad de grabación (0-100, MJPEG) |
| `RECORD_USE_CAMERA_NATIVE` | 0 | 1 = usar resolución nativa de la cámara |
| `RECORD_OUTPUT_DIR` | ./recordings | Carpeta de grabaciones |
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

# 60 FPS estable
FPS_60_MODE=1 python web-cam.py

# Grabación 1920x1080
RECORD_ENABLED=1 RECORD_WIDTH=1920 RECORD_HEIGHT=1080 python web-cam.py

# HTTPS con certificados
SSL_CRT_FILE=cert.pem SSL_KEY_FILE=key.pem python web-cam.py

# HTTPS adhoc (desarrollo)
SSL_ADHOC=1 python web-cam.py
```

## Modos predefinidos (menú)

Ejecuta `python menu.py` para acceder a modos sin escribir variables:

1. Normal (HTTP, 1280x720, 30fps)
2. Alcance largo 80m (640x360, 15fps)
3. Red inestable (buffer + menor calidad)
4. Recursos dinámicos (CPU/RAM ~70%)
5. UDP (transmitir video por red)
6. HTTPS (certificado adhoc)
7. 60 FPS estable (1280x720)
8. Grabar video (máxima calidad, 60fps)

## Endpoints HTTP

| Ruta | Descripción |
|------|-------------|
| `/` | Página con stream y estadísticas |
| `/video_feed` | Stream MJPEG (para `<img src="">` o VLC) |
| `/stats` | JSON con FPS, CPU, memoria, ancho de banda |

## Grabación

Con `--record` o `RECORD_ENABLED=1`:

- Resolución: 1920x1080 por defecto (configurable con `RECORD_WIDTH`, `RECORD_HEIGHT`)
- `RECORD_USE_CAMERA_NATIVE=1`: usa la resolución máxima que reporte la cámara
- `RECORD_QUALITY=95`: calidad de grabación (0-100, aplica a MJPEG cuando el backend lo soporta)
- Salida: `./recordings/recording_YYYYMMDD_HHMMSS.mp4` (o `.avi` si H264/MP4V no están disponibles)
- Códecs probados en orden: avc1, H264, MP4V, MJPEG

Ctrl+C detiene el servidor y cierra el archivo de grabación correctamente.

## Logs

- Consola: métricas cada 10 segundos (FPS, CPU, memoria, ancho de banda)
- Archivo: `stream.log` por defecto (configurable con `LOG_FILE`)

## Detener

Ctrl+C para detener el servidor y liberar la cámara.

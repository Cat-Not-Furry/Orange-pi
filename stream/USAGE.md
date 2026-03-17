# Instrucciones de uso: web-cam.py

Servidor de streaming de video desde cámara USB (compatible con Orange Pi y Raspberry Pi).

## Requisitos

- Python 3
- Dependencias: `opencv-python`, `psutil`, `flask`, `pyopenssl` (solo para HTTPS adhoc)

```bash
pip install -r ../requirements.txt
```

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
| `FRAME_WIDTH` | 1280 | Ancho de frame |
| `FRAME_HEIGHT` | 720 | Alto de frame |
| `FPS` | 30 | Frames por segundo |
| `JPEG_QUALITY` | 80 | Calidad JPEG (0-100) |
| `HTTPS_PORT` | 5000 | Puerto del servidor |
| `FRAME_BUFFER_SIZE` | 0 | Buffer de frames (0=desactivado) |
| `LONG_RANGE_MODE` | 0 | 1 = 640x360, 15fps (alcance 80m) |
| `UNSTABLE_NETWORK_MODE` | 0 | 1 = menor resolución para red inestable |
| `DYNAMIC_RESOURCES` | 0 | 1 = ajuste dinámico CPU/RAM ~70% |
| `UDP_ENABLED` | 0 | 1 = envío UDP activo |
| `UDP_TARGET_IP` | 127.0.0.1 | IP destino UDP |
| `UDP_TARGET_PORT` | 5005 | Puerto destino UDP |
| `RECORD_ENABLED` | 0 | 1 = grabación activa |
| `RECORD_WIDTH` | 1920 | Ancho para grabación |
| `RECORD_HEIGHT` | 1080 | Alto para grabación |
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
7. Grabar video (alta calidad, máxima resolución)

## Endpoints HTTP

| Ruta | Descripción |
|------|-------------|
| `/` | Página con stream y estadísticas |
| `/video_feed` | Stream MJPEG (para `<img src="">` o VLC) |
| `/stats` | JSON con FPS, CPU, memoria, ancho de banda |

## Grabación

Con `--record` o `RECORD_ENABLED=1`:

- Resolución: 1920x1080 por defecto (configurable con `RECORD_WIDTH`, `RECORD_HEIGHT`)
- Salida: `./recordings/recording_YYYYMMDD_HHMMSS.mp4` (o `.avi` si H264/MP4V no están disponibles)
- Códecs probados en orden: avc1, H264, MP4V, MJPEG

Ctrl+C detiene el servidor y cierra el archivo de grabación correctamente.

## Logs

- Consola: métricas cada 10 segundos (FPS, CPU, memoria, ancho de banda)
- Archivo: `stream.log` en el directorio actual

## Detener

Ctrl+C para detener el servidor y liberar la cámara.

# Stream: instrucciones de uso

Streaming de video y GPS desde Orange Pi hacia laptop. El código está separado por dispositivo.

## Menús en la raíz del repositorio

Desde la raíz del proyecto (junto a `stream/`):

**Host (laptop)** — qué protocolo escuchar:

```bash
python host_menu.py
```

**Orange Pi** — TCP o UDP e IP del host (interactivo):

```bash
python orange_menu.py
```

Empareja la misma columna en ambos menús (p. ej. host opción 1 “TCP máxima calidad” + orange: TCP → máxima calidad).

1. **TCP — máxima calidad** ↔ `TCP_QUALITY_MAX=1`
2. **TCP — calidad normal** ↔ `TCP_QUALITY_NORMAL=1`
3. **UDP — máxima calidad** ↔ `UDP_QUALITY_MAX=1`
4. **UDP — máxima transmisión (720p60)** ↔ `UDP_QUALITY_SUPERIOR=1`

`host_menu.py` fija `PYTHONPATH` y lanza `stream/receiver.py`. `orange_menu.py` pide `TCP_HOST` / `UDP_HOST` y ejecuta `python -m stream.tcp.main` o `python -m stream.udp.main`.

## Separación por dispositivo

| Ubicación | Dispositivo | Función |
|-----------|-------------|---------|
| **stream/** (raíz) | Laptop (host) | Recibe, muestra y graba video |
| **stream/tcp/** | Orange Pi (tarjeta) | Captura y transmite por TCP (no graba video) |
| **stream/udp/** | Orange Pi (tarjeta) | Captura y transmite por UDP fragmentado (no graba video) |

## Estructura de directorios

```
stream/
├── recorder.py          # Laptop: recibe HTTP, graba
├── receiver.py          # Laptop: recibe TCP o UDP, graba + GPX
├── USAGE.md
├── .env.example
└── tcp/
    ├── web-cam.py       # Orange Pi: servidor HTTP
    ├── main.py          # Orange Pi: cliente TCP
    ├── gps_reader.py
    ├── video_capture.py
    ├── tcp_sender.py
    ├── data_logger.py   # Orange Pi: backup GPS en CSV (video se graba en laptop)
    ├── resource_limiter.py
    └── pruebas.py
└── udp/
    ├── main.py          # Orange Pi: cliente UDP
    ├── udp_sender.py
    ├── config.py
    └── data_logger.py   # backup GPS en CSV
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
python web-cam.py
```

Menú TCP/UDP con IP del host: desde la raíz del repo, `python orange_menu.py`.

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

Transmisión por TCP con video + GPS. Orange Pi captura y envía; la laptop recibe, muestra, graba video y exporta GPX.

### En laptop (primero)

```bash
cd stream
python receiver.py tcp
# o abreviado (tcp es el valor por defecto):
python receiver.py
```

Espera en puerto 5555 (configurable). Muestra video en tiempo real, graba en segmentos y exporta GPX.

### En Orange Pi

```bash
# Desde la raíz del proyecto (recomendado):
python orange_menu.py
# o manual:
TCP_HOST=192.168.1.50 python -m stream.tcp.main
```

Configura `TCP_HOST` con la IP de la laptop (ej. 192.168.1.50).

### Salidas (en laptop)

- **Video**: `stream/recordings/` (segmentos de 60s)
- **GPX**: `trayectoria_YYYYMMDD_HHMMSS.gpx`

En Orange Pi solo se guarda backup de GPS en `stream/tcp/datos_vuelo/gps_backup.csv` (opcional).

---

## Modo UDP

Transmisión fragmentada por UDP (baja latencia; puede perder paquetes en red inestable). Misma política: grabación y GPX en laptop.

### En laptop (primero)

```bash
cd stream
python receiver.py udp --port 5555
```

### En Orange Pi

Desde la raíz del repositorio:

```bash
UDP_HOST=192.168.1.50 python -m stream.udp.main
```

Mismas resoluciones que TCP si activas `UDP_QUALITY_MAX`, `UDP_QUALITY_SUPERIOR` o `UDP_QUALITY_NORMAL` (solo uno a `1`). Sin ninguno, aplica el modo normal 640x360.

### Salidas (en laptop)

Igual que TCP: `recordings/` y `trayectoria_*.gpx`.

Backup GPS en Orange Pi: `stream/udp/datos_vuelo/gps_backup.csv`.

---

## Menú Orange Pi (TCP / UDP)

Desde la **raíz del repositorio**: `python orange_menu.py` (elige protocolo, IP del host y calidad). HTTP no está en ese menú; usa `web-cam.py` con variables de entorno (p. ej. `MAX_QUALITY_MODE=1`).

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
| `CAMERA_INDICES` | 0,1,2 | Índices de cámara a probar (/dev/video0, video1, video2) |
| `TCP_PORT` | 5555 | Puerto del receptor |
| `GPS_PORT` | /dev/ttyS3 | Puerto serie del GPS |
| `TCP_QUALITY_MAX` | 0 | 1 = 1920x1080 60fps JPEG95 |
| `TCP_QUALITY_SUPERIOR` | 0 | 1 = 1280x720 60fps JPEG90 |
| `TCP_QUALITY_NORMAL` | 0 | 1 = 640x360 30fps JPEG70 |

### UDP (main.py vía `stream.udp.main`)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `UDP_HOST` | - | IP de la laptop (obligatorio) |
| `UDP_PORT` | 5555 | Puerto donde escucha `receiver.py udp` |
| `UDP_PACKET_SIZE` | 1400 | Tamaño máximo del datagrama (payload + cabecera) |
| `UDP_QUALITY_MAX` | 0 | 1 = 1920x1080 60fps JPEG95 |
| `UDP_QUALITY_SUPERIOR` | 0 | 1 = 1280x720 60fps JPEG90 |
| `UDP_QUALITY_NORMAL` | 0 | 1 = 640x360 30fps JPEG70 |

`CAMERA_INDICES`, `GPS_PORT` y `GPS_BAUD` se comparten con TCP.

---

## Comandos rápidos

### Orange Pi

```bash
python orange_menu.py
cd stream/tcp && python web-cam.py
# o: python -m stream.tcp.main | python -m stream.udp.main
```

### Laptop

```bash
# Menús (raíz del repo): laptop → python host_menu.py | Orange Pi → python orange_menu.py

cd stream
python receiver.py tcp
python receiver.py udp
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

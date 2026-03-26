# Stream: instrucciones de uso

Envío de **imágenes JPEG** por **UDP** (fragmentado) con GPS desde Orange Pi hacia laptop. **No hay grabación de vídeo en vivo** (`VideoWriter` / MP4 en el receptor): solo **JPEG sueltos** en disco para análisis (Pi) y para **montar vídeo offline** después (laptop).

La **sesión** (nombre de subcarpeta) la genera **la Orange Pi** al arrancar el emisor; va en **cada datagrama** para que la laptop cree la misma ruta sin depender del orden de arranque.

## Menús en la raíz del repositorio

**Host (laptop)** — receptor UDP:

```bash
python host_menu.py
```

**Orange Pi** — emisor e IP del host:

```bash
python orange_menu.py
```

`host_menu.py` fija `PYTHONPATH` y lanza `stream/img_udp/receiver.py` con `--recordings-base` = `<repo>/recordings`. `orange_menu.py` define `UDP_DEST_IP` y ejecuta `python -m stream.img_udp.main`.

## Dónde se guardan los datos

Raíz del repo: [PROJECT_ROOT]/`recordings`/`<session_id>`/

| Subcarpeta | Dispositivo | Contenido |
|------------|-------------|-----------|
| `analysis/` | Orange Pi | JPEG y `.gps` en **máxima calidad de captura** (recomendado `ORANGE_ANALYSIS_MAX=1` o subir `JPEG_QUALITY`) |
| `video_source/` | Laptop | JPEG re-codificados con `HOST_SAVE_JPEG_QUALITY` (menor tamaño, adecuados para timeline de vídeo) |

`session_id` por defecto: fecha-hora local `%Y-%m-%d_%H-%M-%S`. Override: variable `SESSION_ID` (máx. 31 caracteres UTF-8 en cabecera UDP).

## Separación por dispositivo

| Ubicación | Dispositivo | Función |
|-----------|-------------|-----------|
| `stream/img_udp/receiver.py` | Laptop | Reensambla JPEG, vista previa, guarda en `video_source/` |
| `stream/common/` | Ambos | `config`, `gps_reader`, `video_capture`, `resource_limiter` |
| `stream/img_udp/` | Orange Pi | `main.py`, `sender.py` |

## Estructura de directorios

```text
<repo>/
├── recordings/             # creado por sesión; ignorado por git
│   └── <session_id>/
│       ├── analysis/       # sólo en Orange Pi
│       └── video_source/   # sólo en laptop
├── stream/
│   ├── common/
│   ├── img_udp/
│   ├── datos_vuelo/        # legado opcional
│   ├── recorder.py         # HTTP/MJPEG opcional
│   ├── receiver.py         # delega en img_udp/receiver.py
│   ├── USAGE.md
│   └── .env.example
├── host_menu.py
└── orange_menu.py
```

## Requisitos

- Python 3
- `opencv-python`, `numpy`, `psutil`, `pynmea2`, `pyserial` en la Pi si usas GPS

```bash
pip install -r requirements.txt
```

## Modo UDP imágenes (principal)

### En la laptop

Desde la raíz del repo (para imports `stream.*`):

```bash
PYTHONPATH=. python -m stream.img_udp.receiver
```

O desde `stream/`:

```bash
cd stream
PYTHONPATH=.. python img_udp/receiver.py --recordings-base ../recordings
```

`host_menu.py` ya pasa `--recordings-base` apuntando a `<repo>/recordings`.

Opciones útiles:

- `--recordings-base`: raíz (default: `RECORDINGS_DIR` en config = `<repo>/recordings`)
- `--no-save-frames`: solo ventana OpenCV
- `--host-jpeg-quality N`: calidad al escribir en `video_source/`
- `--port`, `--bind`
- Tecla `q` cierra la ventana

### En Orange Pi

```bash
# Desde la raíz del repo:
UDP_DEST_IP=192.168.1.50 python -m stream.img_udp.main

# Sesión explícita:
SESSION_ID=vuelo_001 UDP_DEST_IP=192.168.1.50 python -m stream.img_udp.main

# Máxima calidad JPEG para carpeta analysis/ (también es lo que sale por UDP):
ORANGE_ANALYSIS_MAX=1 UDP_DEST_IP=... python -m stream.img_udp.main
```

## Variables de entorno (resumen)

Cabecera UDP: `IMG_UDP_HEADER_FORMAT` en `stream/common/config.py` (incluye `session_id` 32 bytes + metadatos + payload).

| Variable | Default | Descripción |
|----------|---------|-------------|
| `SESSION_ID` | (fecha hora) | Nombre de sesión (Pi); máx. 31 chars |
| `RECORDINGS_DIR` | `<repo>/recordings` | Raíz de sesiones en ambos equipos si misma convención |
| `ANALYSIS_SUBDIR` | analysis | Subcarpeta en Pi |
| `VIDEO_SOURCE_SUBDIR` | video_source | Subcarpeta en laptop |
| `SAVE_LOCAL_ANALYSIS` | 1 | Guardar JPEG en Pi bajo `recordings/<session>/analysis/` |
| `SAVE_HOST_FRAMES` | 1 | Guardar JPEG en laptop (`--no-save-frames` lo desactiva) |
| `HOST_SAVE_JPEG_QUALITY` | 75 | Calidad al re-encode en laptop |
| `ORANGE_ANALYSIS_MAX` | 0 | 1 → sube `ANALYSIS_JPEG_QUALITY` (default 98) para captura |
| `ANALYSIS_JPEG_QUALITY` | 98 | Si `ORANGE_ANALYSIS_MAX=1` |
| `UDP_DEST_IP` / `UDP_HOST` | (vacío) | IP laptop; obligatorio en emisor |
| `UDP_PORT` | 5555 | Emisor y receptor |
| `UDP_PACKET_SIZE` | 1400 | MTU lógica |
| `UDP_RETRANSMIT` | 0 | Copias por fragmento (mínimo 1 envío real) |
| `IMG_UDP_QUALITY_MAX` / `SUPERIOR` | 0 | Perfiles resolución/FPS |

Ver `stream/.env.example`.

## Modo HTTP (opcional)

`recorder.py` para un servidor MJPEG externo; no está en `orange_menu.py`.

---

## Comandos rápidos

**Orange Pi:** `python orange_menu.py` o `UDP_DEST_IP=... python -m stream.img_udp.main`

**Laptop:** `python host_menu.py` o `PYTHONPATH=. python -m stream.img_udp.receiver`

## Detener

Ctrl+C en emisor o receptor; en la ventana OpenCV, `q`.

# Checklist: Variables dinámicas multi-plataforma

Plan para que el proyecto funcione en Orange Pi y Raspberry Pi sin modificar código.
Stack actual: **UDP imágenes** (`stream/common/`, `stream/img_udp/`).

---

## Checklist del agente

### 1. stream/common/config.py

- [x] **CAMERA_INDICES**, **FRAME_***, **JPEG_***, **ROTATE**, **MAX_QUEUE_SIZE** desde env.
- [x] **UDP_***, **GPS_***, **SAVE_LOCAL_IMAGES**, perfiles **IMG_UDP_QUALITY_***.
- [x] **IMG_UDP_HEADER_FORMAT** / **IMG_UDP_HEADER_SIZE** alineados con emisor y receptor.

### 2. stream/common/resource_limiter.py

- [x] Umbrales **MAX_CPU_PERCENT** / **MAX_MEMORY_PERCENT** (lectura de uso con psutil).

### 3. Menús en la raíz del repo

- [x] **host_menu.py** / **orange_menu.py**: receptor UDP imágenes en laptop y emisor desde Orange Pi con IP interactiva.

### 4. stream/.env.example

- [x] Variables UDP imágenes, vídeo, GPS y límites documentadas.

### 5. stream/USAGE.md

- [x] Modo UDP imágenes, rutas `common/` e `img_udp/`, variables de entorno.

### 6. Verificación

- [x] Ejecutar `python -m py_compile stream/common/*.py stream/img_udp/*.py` (desde raíz con imports resueltos).
- [x] Ejecutar `python -m py_compile orange_menu.py host_menu.py` (raíz del repo).

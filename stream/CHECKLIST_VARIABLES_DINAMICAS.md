# Checklist: Variables dinámicas multi-plataforma

Plan para que el proyecto funcione en Orange Pi y Raspberry Pi sin modificar código.
Incluye: host-only, 60 FPS estable, grabación máxima calidad.

---

## Checklist del agente

### 1. stream/web-cam.py

- [x] **CAMERA_INDICES**: Lectura desde env (default "0,1,2"), parseado a lista de enteros.
- [x] **LOG_FILE**: Variable desde env, usada en FileHandler.
- [x] **PAGE_TITLE**: Variable desde env, usada en `<title>` del HTML.
- [x] **Template HTML**: `frame_width`, `frame_height` dinámicos en `<img>`.
- [x] **FPS_60_MODE**: Modo 1280x720 a 60 fps.
- [x] **RECORD_QUALITY**: Aplicada en VideoWriter (VIDEOWRITER_PROP_QUALITY).
- [x] **RECORD_USE_CAMERA_NATIVE**: Resolución nativa de cámara (3840x2160 solicitado).

### 2. stream/resource_limiter.py

- [x] **RESOURCE_INITIAL_LEVEL**: Parámetro desde env.
- [x] **FPS_60_MODE + DYNAMIC_RESOURCES**: initial_level=7 para arrancar en 60 fps.

### 3. stream/menu.py

- [x] **Opción "60 FPS estable (1280x720)"**.
- [x] **Modo grabación máxima**: RECORD_QUALITY=95, FPS=60, JPEG_QUALITY=95.

### 4. stream/.env.example

- [x] CAMERA_INDICES, LOG_FILE, PAGE_TITLE.
- [x] FPS_60_MODE, RESOURCE_INITIAL_LEVEL.
- [x] RECORD_QUALITY, RECORD_USE_CAMERA_NATIVE, RECORD_*.

### 5. stream/USAGE.md

- [x] Sección "Requisitos de red (solo conexión a host)".
- [x] Nuevas variables documentadas.
- [x] Modos menú actualizados.

### 6. Verificación

- [x] Ejecutar `python -m py_compile stream/web-cam.py`.
- [x] Ejecutar `python -m py_compile stream/resource_limiter.py`.
- [x] Ejecutar `python -m py_compile stream/menu.py`.

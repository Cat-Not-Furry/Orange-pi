# Resultados de pruebas de streaming

Anota aquí las métricas obtenidas al probar cada configuración.
Ejecuta el servidor con `python pruebas.py --width W --height H --fps F --jpeg J`
y observa los logs cada 10 segundos.

| Resolución | FPS | Calidad JPEG | FPS real (medido) | CPU % | Ancho de banda (aprox) | Latencia percibida |
|------------|-----|--------------|-------------------|-------|------------------------|--------------------|
| 1280x720   | 30  | 80           | -                 | -     | -                      | -                  |
| 854x480    | 25  | 70           | -                 | -     | -                      | -                  |
| 640x360    | 20  | 60           | -                 | -     | -                      | -                  |
| 640x360    | 15  | 50           | -                 | -     | -                      | -                  |
| 480x270    | 15  | 50           | -                 | -     | -                      | -                  |

## Notas

- **FPS real**: valor mostrado en el log MÉTRICAS
- **CPU %**: valor del log
- **Ancho de banda**: valor BW en Mbps del log
- **Latencia percibida**: subjetiva (baja/media/alta)

## Generación de certificados autofirmados (HTTPS)

Para probar el stream con HTTPS en red local:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=orange-pi.local"
```

Luego ejecutar:

```bash
SSL_CRT_FILE=cert.pem SSL_KEY_FILE=key.pem python web-cam.py
```

O con certificado adhoc (solo desarrollo, requiere pyopenssl):

```bash
SSL_ADHOC=1 python web-cam.py
```

**Nota**: HTTPS añade cifrado y puede aumentar el uso de CPU en Orange Pi. Anota el impacto en la tabla de métricas.

## Alcance 80m

Para alcance efectivo mínimo de 80 metros:

- **LONG_RANGE_MODE=1**: aplica 640x360, 15 FPS, JPEG 60 automáticamente
- Usar **2.4 GHz** (mejor penetración que 5 GHz)
- Antena externa de mayor ganancia si el WiFi integrado no alcanza
- Reducir obstáculos entre dron y estación de tierra

```bash
LONG_RANGE_MODE=1 python web-cam.py
# o con buffer para mayor estabilidad:
LONG_RANGE_MODE=1 FRAME_BUFFER_SIZE=5 python web-cam.py
```

## Modo red inestable

Cuando la red es inestable (WiFi con pérdida de paquetes, distancia variable):

- **FRAME_BUFFER_SIZE=5-10**: buffer de frames para reconexión rápida
- **UNSTABLE_NETWORK_MODE=1**: reduce resolución, FPS y calidad JPEG

```bash
UNSTABLE_NETWORK_MODE=1 FRAME_BUFFER_SIZE=8 python web-cam.py
```

El cliente detecta desconexión (3 fallos consecutivos en `/stats`) y recarga el stream automáticamente.

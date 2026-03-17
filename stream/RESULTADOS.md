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

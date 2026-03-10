#!/usr/bin/env python3
"""
Script para mostrar video de cámara USB en el framebuffer (pantalla física)
sin necesidad de entorno gráfico X11.
"""

import cv2
import numpy as np
import os
import sys
import time
import fcntl
import struct

# Configuración
CAMERA_INDEX = 0  # Cambia si tu cámara es otro índice
FRAME_WIDTH = 640  # Ancho deseado
FRAME_HEIGHT = 480  # Alto deseado
FB_DEVICE = "/dev/fb0"  # Dispositivo framebuffer
FORMAT = "bgra"  # Formato de píxel para el framebuffer (común)


def get_fb_info():
    """
    Obtiene la resolución y bits por píxel del framebuffer usando ioctl.
    Retorna (ancho, alto, bits_por_pixel) o (None, None, None) si falla.
    """
    try:
        fb = os.open(FB_DEVICE, os.O_RDWR)
        # Constante FBIOGET_VSCREENINFO = 0x4600
        # Struct fb_var_screeninfo (simplificada)
        buf = fcntl.ioctl(fb, 0x4600, " " * 100)
        os.close(fb)
        # Desempaquetar los primeros campos: xres (4 bytes), yres (4 bytes), bits_per_pixel (4 bytes)
        xres = struct.unpack("I", buf[0:4])[0]
        yres = struct.unpack("I", buf[4:8])[0]
        bpp = struct.unpack("I", buf[12:16])[0]
        return xres, yres, bpp
    except Exception as e:
        print(f"Error obteniendo info del framebuffer: {e}")
        return None, None, None


def main():
    # 1. Obtener información del framebuffer
    fb_width, fb_height, fb_bpp = get_fb_info()
    if fb_width is None:
        print("No se pudo determinar la resolución del framebuffer.")
        print("Usando valores por defecto (1920x1080). Ajusta según tu monitor.")
        fb_width, fb_height = 1920, 1080
        fb_bpp = 32
    else:
        print(f"Framebuffer detectado: {fb_width}x{fb_height}, {fb_bpp} bpp")

    # 2. Abrir cámara
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: No se puede abrir la cámara con índice {CAMERA_INDEX}")
        print("Prueba con otro índice (1, 2, ...) o verifica la conexión.")
        sys.exit(1)

    # Configurar resolución de captura
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    # 3. Abrir framebuffer para escritura
    try:
        fb = os.open(FB_DEVICE, os.O_RDWR)
    except Exception as e:
        print(f"Error abriendo {FB_DEVICE}: {e}")
        print("Asegúrate de tener permisos (ejecuta con sudo).")
        sys.exit(1)

    print("Mostrando video en framebuffer. Presiona Ctrl+C para salir.")

    try:
        while True:
            # Capturar frame
            ret, frame = cap.read()
            if not ret:
                print("Error leyendo frame de la cámara")
                break

            # Redimensionar al tamaño del framebuffer
            # (Si quieres mantener proporción, puedes hacer un resize ajustado)
            frame_resized = cv2.resize(frame, (fb_width, fb_height))

            # Convertir al formato esperado por el framebuffer
            # OpenCV por defecto usa BGR, necesitamos BGRA (32 bits) que suele ser compatible
            # Si fb_bpp es 16, habría que convertir a rgb565, pero por el error sabemos que no es soportado.
            # Asumimos 32 bits.
            if fb_bpp == 32:
                frame_fb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2BGRA)
            elif fb_bpp == 16:
                # Intentar convertir a BGR565 (poco común, pero por si acaso)
                frame_fb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2BGR565)
            else:
                print(f"Bits por píxel {fb_bpp} no soportado. Usando BGRA.")
                frame_fb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2BGRA)

            # Escribir en el framebuffer (empezando desde el inicio)
            os.lseek(fb, 0, os.SEEK_SET)
            os.write(fb, frame_fb.tobytes())

            # Pequeña pausa para controlar FPS (ajusta según necesites)
            time.sleep(0.03)  # ~30 FPS

    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    except Exception as e:
        print(f"Error durante la reproducción: {e}")
    finally:
        # Liberar recursos
        cap.release()
        os.close(fb)
        print("Recursos liberados.")


if __name__ == "__main__":
    main()

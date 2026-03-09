#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import sys


def main():
    # --- Configuración ---
    # Índice de la cámara. Normalmente 0 es la primera cámara (USB o integrada).
    # En algunos casos, como en Raspberry Pi o si tienes múltiples cámaras, puede ser 1, 2, etc.
    camera_index = 0
    # Ancho y alto deseados para la ventana (opcional, comenta si quieres la resolución por defecto)
    frame_width = 640
    frame_height = 480
    # ---------------------

    # Inicializar la captura de video
    print(f"[INFO] Intentando abrir la cámara con índice {camera_index}...")
    cap = cv2.VideoCapture(camera_index)

    # Verificar si la cámara se abrió correctamente
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir la cámara con índice {camera_index}.")
        print(
            "[INFO] Prueba cambiando el 'camera_index' en el script (a 1, 2, etc.) o verifica la conexión de la cámara."
        )
        sys.exit(1)

    # Configurar la resolución (opcional)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    print(
        f"[INFO] Cámara abierta. Resolución configurada a {frame_width}x{frame_height}."
    )

    print("[INFO] Mostrando video. Presiona 'q' en la ventana para salir.")

    while True:
        # Capturar frame por frame
        ret, frame = cap.read()

        # Si el frame se capturó correctamente, 'ret' será True
        if not ret:
            print("[ERROR] No se pudo recibir el frame. Saliendo...")
            break

        # Mostrar el frame en una ventana
        cv2.imshow("Video en Tiempo Real - Presiona q para salir", frame)

        # Salir del bucle si se presiona la tecla 'q'
        # cv2.waitKey(1) espera 1 ms por una tecla. El & 0xFF es necesario para sistemas de 64 bits.
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[INFO] Tecla 'q' presionada. Saliendo...")
            break

    # Liberar la cámara y cerrar todas las ventanas
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Programa terminado.")


if __name__ == "__main__":
    main()

#!/bin/bash
# Script mínimo para reproducir video en Orange Pi usando framebuffer (sin X11)
# Dependencias: ffmpeg, fbset (opcional para autodetección de resolución)
# Uso: ./ver-video.sh <archivo_video> [resolución] [formato_pixel]

set -e

# Colores para mensajes (opcional)
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
ROJO='\033[0;31m'
NC='\033[0m' # Sin color

# Mostrar ayuda si no hay argumentos
if [ $# -lt 1 ]; then
  echo -e "${VERDE}Reproductor de video para framebuffer (Orange Pi)${NC}"
  echo "Uso: $0 <archivo_video> [resolución] [formato_pixel]"
  echo ""
  echo "Parámetros:"
  echo "  archivo_video   Ruta al archivo de video (MP4, AVI, etc.)"
  echo "  resolución       Opcional: ancho x alto (ej. 1280x720). Por defecto se detecta automáticamente."
  echo "  formato_pixel    Opcional: formato para framebuffer (rgb565, bgra, rgb888). Por defecto se detecta."
  echo ""
  echo "Ejemplos:"
  echo "  $0 video.mp4"
  echo "  $0 video.avi 640x480 rgb565"
  echo "  $0 /ruta/completa/video.mkv 1280x720 bgra"
  exit 0
fi

# Parámetros
VIDEO="$1"
RESOLUCION="$2"
PIXFMT="$3"

# Verificar que el archivo existe
if [ ! -f "$VIDEO" ]; then
  echo -e "${ROJO}Error: No se encuentra el archivo '$VIDEO'${NC}"
  exit 1
fi

# Verificar que ffmpeg está instalado
if ! command -v ffmpeg &>/dev/null; then
  echo -e "${ROJO}Error: ffmpeg no está instalado. Instálalo con: sudo apt install ffmpeg${NC}"
  exit 1
fi

# Verificar que el framebuffer existe
if [ ! -e /dev/fb0 ]; then
  echo -e "${ROJO}Error: No se encuentra /dev/fb0. El framebuffer puede no estar habilitado.${NC}"
  exit 1
fi

# Si no se especificó resolución, intentar detectarla con fbset
if [ -z "$RESOLUCION" ]; then
  if command -v fbset &>/dev/null; then
    RESOLUCION=$(fbset -s | grep geometry | awk '{print $2"x"$3}')
    if [ -n "$RESOLUCION" ]; then
      echo -e "${VERDE}Resolución detectada: $RESOLUCION${NC}"
    else
      RESOLUCION="640x480"
      echo -e "${AMARILLO}No se pudo detectar resolución, usando 640x480${NC}"
    fi
  else
    RESOLUCION="640x480"
    echo -e "${AMARILLO}fbset no instalado, usando resolución por defecto 640x480. Para mejor resultado, instala fbset.${NC}"
  fi
fi

# Si no se especificó formato de píxel, intentar detectar con fbset
if [ -z "$PIXFMT" ]; then
  if command -v fbset &>/dev/null; then
    # Analizar salida de fbset para determinar formato común
    RGBA=$(fbset -s | grep rgba)
    if [[ "$RGBA" == *"5/11,6/5,5/0"* ]]; then
      PIXFMT="rgb565"
    elif [[ "$RGBA" == *"8/16,8/8,8/0"* ]]; then
      PIXFMT="rgb888"
    else
      PIXFMT="bgra"
    fi
  else
    PIXFMT="bgra"
  fi
  echo -e "${VERDE}Formato de píxel seleccionado: $PIXFMT${NC}"
fi

# Construir comando ffmpeg
CMD="ffmpeg -i \"$VIDEO\" -s $RESOLUCION -pix_fmt $PIXFMT -f fbdev /dev/fb0"

echo -e "${AMARILLO}Reproduciendo: $VIDEO"
echo -e "Resolución: $RESOLUCION | Formato: $PIXFMT${NC}"
echo -e "Presiona Ctrl+C para salir."

# Ejecutar con permisos adecuados
if [ -w /dev/fb0 ]; then
  eval $CMD
else
  echo -e "${AMARILLO}No tienes permisos de escritura en /dev/fb0. Usando sudo...${NC}"
  sudo -E env "PATH=$PATH" eval $CMD
fi

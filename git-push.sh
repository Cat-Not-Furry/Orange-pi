#!/bin/bash
# Script para automatizar git add, commit y push
# Uso: gitpush "Mensaje del commit" (opcional)
# Si no se proporciona mensaje, usa "Update <fecha>"

set -e # Salir si algún comando falla

# Colores para mensajes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en un repositorio git
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo -e "${RED}Error: No estás dentro de un repositorio Git.${NC}"
  exit 1
fi

# Obtener la rama actual
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
if [ -z "$BRANCH" ]; then
  echo -e "${RED}Error: No se pudo determinar la rama actual (modo detached HEAD?).${NC}"
  exit 1
fi

# Mostrar estado actual
echo -e "${YELLOW}Repositorio en rama: ${GREEN}$BRANCH${NC}"
echo -e "${YELLOW}Estado actual:${NC}"
git status -s

# Preguntar si queremos continuar
read -p "¿Continuar con add/commit/push? (s/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Ss]$ ]]; then
  echo "Operación cancelada."
  exit 0
fi

# Añadir todos los cambios (incluyendo nuevos y eliminados)
echo -e "${YELLOW}Añadiendo cambios...${NC}"
git add -A

# Verificar si hay algo para commit
if git diff --cached --quiet; then
  echo -e "${YELLOW}No hay cambios para commit.${NC}"
  exit 0
fi

# Determinar mensaje del commit
if [ $# -ge 1 ]; then
  COMMIT_MSG="$*"
else
  COMMIT_MSG="Update $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Hacer commit
echo -e "${YELLOW}Haciendo commit con mensaje: ${GREEN}$COMMIT_MSG${NC}"
git commit -m "$COMMIT_MSG"

# Hacer push
echo -e "${YELLOW}Haciendo push a origin/$BRANCH...${NC}"
git push origin "$BRANCH"

echo -e "${GREEN}¡Proceso completado con éxito!${NC}"

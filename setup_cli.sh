#!/bin/bash
# ============================================================================
# Cyber-Triage CLI Setup Script
# Setup rápido en EC2 sin necesidad de port forwarding
# ============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🛡️  Cyber-Triage CLI Setup"
echo "=========================================="
echo ""

# Verificar Python
echo -e "${GREEN}[1/5]${NC} Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "  ✅ $PYTHON_VERSION"
else
    echo -e "${RED}  ❌ Python 3 no encontrado${NC}"
    exit 1
fi

# Verificar pip
echo -e "${GREEN}[2/5]${NC} Verificando pip..."
if command -v pip3 &> /dev/null; then
    echo "  ✅ pip instalado"
else
    echo -e "${YELLOW}  ⚠️  Instalando pip...${NC}"
    sudo yum install -y python3-pip
fi

# Instalar dependencias
echo -e "${GREEN}[3/5]${NC} Instalando dependencias..."
pip3 install -r requirements.txt --break-system-packages --quiet

if [ $? -eq 0 ]; then
    echo "  ✅ Dependencias instaladas"
else
    echo -e "${RED}  ❌ Error instalando dependencias${NC}"
    exit 1
fi

# Verificar .env
echo -e "${GREEN}[4/5]${NC} Verificando configuración..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}  ⚠️  Archivo .env no encontrado${NC}"
    echo "  Creando desde .env.example..."
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}=========================================="
    echo "⚠️  ACCIÓN REQUERIDA"
    echo "==========================================${NC}"
    echo ""
    echo "Edita el archivo .env con tus credenciales:"
    echo "  nano .env"
    echo ""
    echo "Variables obligatorias:"
    echo "  - GEMINI_API_KEY"
    echo "  - CYBERHAVEN_API_KEY"
    echo ""
    echo "Nota: AWS credentials NO son necesarias si"
    echo "      esta EC2 tiene IAM Role con permisos S3"
    echo ""
    read -p "Presiona Enter cuando hayas configurado .env..."
fi

source .env

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" == "your-gemini-api-key-here" ]; then
    echo -e "${RED}  ❌ GEMINI_API_KEY no configurada${NC}"
    echo "  Edita .env y configura las API keys"
    exit 1
fi

echo "  ✅ Configuración verificada"

# Crear directorios necesarios
echo -e "${GREEN}[5/5]${NC} Creando directorios..."
mkdir -p data evidencia_temp logs prompts
echo "  ✅ Directorios creados"

echo ""
echo "=========================================="
echo "✅ Setup Completado"
echo "=========================================="
echo ""
echo "Para ejecutar el sistema:"
echo "  python3 cyber_triage_cli.py"
echo ""
echo "Comandos útiles:"
echo "  • Ver logs:        tail -f logs/app.log"
echo "  • Editar config:   nano .env"
echo "  • Actualizar deps: pip3 install -r requirements.txt --upgrade"
echo ""
echo "=========================================="

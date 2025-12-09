#!/bin/bash
# ============================================================================
# Cyber-Triage CLI - One-Click Setup & Launch
# Ejecuta setup completo y lanza el CLI automáticamente
# ============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🛡️  CYBER-TRIAGE CLI - ONE-CLICK SETUP        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Función: Instalar dependencias del sistema
# ============================================================================
install_system_deps() {
    echo -e "${GREEN}[1/6]${NC} Verificando dependencias del sistema..."
    
    # Python 3
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}  Instalando Python 3...${NC}"
        sudo yum install -y python3
    fi
    echo "  ✅ Python: $(python3 --version)"
    
    # pip
    if ! command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}  Instalando pip...${NC}"
        sudo yum install -y python3-pip
    fi
    echo "  ✅ pip instalado"
    
    # Git
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}  Instalando Git...${NC}"
        sudo yum install -y git
    fi
    echo "  ✅ Git instalado"
    
    echo ""
}

# ============================================================================
# Función: Instalar dependencias Python
# ============================================================================
install_python_deps() {
    echo -e "${GREEN}[2/6]${NC} Instalando dependencias Python..."
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt --break-system-packages --quiet
        
        if [ $? -eq 0 ]; then
            echo "  ✅ Dependencias instaladas"
        else
            echo -e "${RED}  ❌ Error instalando dependencias${NC}"
            exit 1
        fi
    else
        echo -e "${RED}  ❌ requirements.txt no encontrado${NC}"
        exit 1
    fi
    
    echo ""
}

# ============================================================================
# Función: Crear directorios
# ============================================================================
setup_directories() {
    echo -e "${GREEN}[3/6]${NC} Configurando directorios..."
    
    mkdir -p data evidencia_temp logs prompts
    
    echo "  ✅ Directorios creados"
    echo ""
}

# ============================================================================
# Función: Configurar .env
# ============================================================================
setup_env() {
    echo -e "${GREEN}[4/6]${NC} Configurando variables de entorno..."
    
    if [ -f ".env" ]; then
        echo "  ✅ .env ya existe"
        
        # Validar que tenga API keys
        source .env
        
        if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" == "your-gemini-api-key-here" ]; then
            echo -e "${RED}  ❌ GEMINI_API_KEY no configurada correctamente${NC}"
            echo ""
            echo "Edita .env y agrega tu API key de Gemini:"
            echo "  nano .env"
            echo ""
            exit 1
        fi
        
        if [ -z "$CYBERHAVEN_API_KEY" ] || [ "$CYBERHAVEN_API_KEY" == "your-cyberhaven-refresh-token" ]; then
            echo -e "${RED}  ❌ CYBERHAVEN_API_KEY no configurada correctamente${NC}"
            echo ""
            echo "Edita .env y agrega tu refresh token de Cyberhaven:"
            echo "  nano .env"
            echo ""
            exit 1
        fi
        
        echo "  ✅ API keys configuradas"
    else
        echo -e "${YELLOW}  ⚠️  .env no encontrado, creando desde template...${NC}"
        
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo ""
            echo -e "${YELLOW}╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║  ⚠️  ACCIÓN REQUERIDA                          ║${NC}"
            echo -e "${YELLOW}╚══════════════════════════════════════════════════╝${NC}"
            echo ""
            echo "Antes de continuar, debes configurar .env con tus credenciales:"
            echo ""
            echo "  nano .env"
            echo ""
            echo "Variables obligatorias:"
            echo "  - GEMINI_API_KEY=tu-api-key-aquí"
            echo "  - CYBERHAVEN_API_KEY=tu-refresh-token-aquí"
            echo ""
            echo "Después de guardar, ejecuta de nuevo este script:"
            echo "  ./start_cli.sh"
            echo ""
            exit 0
        else
            echo -e "${RED}  ❌ .env.example no encontrado${NC}"
            exit 1
        fi
    fi
    
    echo ""
}

# ============================================================================
# Función: Verificar IAM Role
# ============================================================================
check_iam() {
    echo -e "${GREEN}[5/6]${NC} Verificando acceso a AWS..."
    
    if curl -s -f http://169.254.169.254/latest/meta-data/iam/security-credentials/ > /dev/null 2>&1; then
        IAM_ROLE=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)
        echo "  ✅ IAM Role detectado: $IAM_ROLE"
        echo "  ℹ️  boto3 usará automáticamente estas credenciales"
    else
        echo -e "${YELLOW}  ⚠️  No se detectó IAM Role${NC}"
        echo "  ℹ️  Asegúrate de tener AWS credentials en .env"
    fi
    
    echo ""
}

# ============================================================================
# Función: Test rápido
# ============================================================================
run_quick_test() {
    echo -e "${GREEN}[6/6]${NC} Ejecutando test rápido..."
    echo ""
    
    if [ -f "quick_test.py" ]; then
        python3 quick_test.py
        
        if [ $? -ne 0 ]; then
            echo ""
            echo -e "${RED}❌ Algunos tests fallaron${NC}"
            echo "Revisa los errores arriba y corrige antes de continuar."
            echo ""
            exit 1
        fi
    else
        echo -e "${YELLOW}  ⚠️  quick_test.py no encontrado, saltando tests${NC}"
    fi
    
    echo ""
}

# ============================================================================
# Función: Lanzar CLI
# ============================================================================
launch_cli() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ SETUP COMPLETADO                            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Iniciando Cyber-Triage CLI en 3 segundos..."
    echo ""
    sleep 3
    
    python3 cyber_triage_cli.py
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    # Verificar que estamos en el directorio correcto
    if [ ! -f "cyber_triage_cli.py" ]; then
        echo -e "${RED}❌ cyber_triage_cli.py no encontrado${NC}"
        echo "Asegúrate de estar en el directorio Cyber-Triage:"
        echo "  cd ~/Cyber-Triage"
        exit 1
    fi
    
    # Ejecutar setup paso a paso
    install_system_deps
    install_python_deps
    setup_directories
    setup_env
    check_iam
    run_quick_test
    
    # Preguntar si quiere lanzar ahora
    echo ""
    echo -e "${BLUE}¿Quieres lanzar Cyber-Triage CLI ahora? (y/n)${NC}"
    read -p "> " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        launch_cli
    else
        echo ""
        echo "Setup completado. Puedes lanzar el CLI cuando quieras con:"
        echo "  python3 cyber_triage_cli.py"
        echo ""
    fi
}

# Ejecutar
main

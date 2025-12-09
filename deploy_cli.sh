#!/bin/bash
# ============================================================================
# Cyber-Triage CLI - Docker Deployment Script
# ============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🛡️  CYBER-TRIAGE CLI - DOCKER SETUP           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

APP_NAME="cyber-triage-cli"
CONTAINER_NAME="cyber-triage-cli"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Verificar Docker
# ============================================================================
log_info "Verificando Docker..."

if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado. Instalando..."
    sudo yum update -y
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    log_info "Docker instalado. Reinicia la sesión para aplicar permisos de grupo."
    exit 0
fi

log_info "✅ Docker instalado: $(docker --version)"

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose no está instalado. Instalando..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_info "Docker Compose instalado."
fi

log_info "✅ Docker Compose instalado: $(docker-compose --version)"
echo ""

# ============================================================================
# Verificar .env
# ============================================================================
log_info "Verificando configuración (.env)..."

if [ ! -f ".env" ]; then
    log_error ".env no encontrado!"
    
    if [ -f ".env.example" ]; then
        log_info "Creando .env desde template..."
        cp .env.example .env
        log_warn "⚠️  IMPORTANTE: Edita .env con tus credenciales:"
        log_warn "   nano .env"
        log_warn ""
        log_warn "Variables obligatorias:"
        log_warn "  - GEMINI_API_KEY"
        log_warn "  - CYBERHAVEN_API_KEY"
        echo ""
        read -p "¿Quieres editar .env ahora? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            nano .env
        else
            log_error "Deployment cancelado. Configura .env y vuelve a ejecutar."
            exit 1
        fi
    else
        log_error ".env.example no encontrado. Crea .env manualmente."
        exit 1
    fi
fi

source .env

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" == "your-gemini-api-key-here" ]; then
    log_error "GEMINI_API_KEY no configurada correctamente en .env"
    exit 1
fi

if [ -z "$CYBERHAVEN_API_KEY" ] || [ "$CYBERHAVEN_API_KEY" == "your-cyberhaven-refresh-token" ]; then
    log_error "CYBERHAVEN_API_KEY no configurada correctamente en .env"
    exit 1
fi

log_info "✅ Variables de entorno configuradas"
echo ""

# ============================================================================
# Verificar IAM Role (opcional para AWS)
# ============================================================================
log_info "Verificando acceso a AWS..."

if curl -s -f http://169.254.169.254/latest/meta-data/iam/security-credentials/ > /dev/null 2>&1; then
    IAM_ROLE=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)
    log_info "✅ IAM Role detectado: $IAM_ROLE"
else
    log_warn "⚠️  No se detectó IAM Role. Asegúrate de tener AWS credentials en .env"
fi
echo ""

# ============================================================================
# Detener contenedor anterior
# ============================================================================
log_info "Deteniendo contenedor anterior (si existe)..."

if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    log_info "Deteniendo contenedor activo..."
    docker stop $CONTAINER_NAME
fi

if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    log_info "Eliminando contenedor..."
    docker rm $CONTAINER_NAME
fi

log_info "✅ Limpieza completada"
echo ""

# ============================================================================
# Build imagen
# ============================================================================
log_info "Construyendo imagen Docker..."

docker build -t $APP_NAME:latest .

if [ $? -eq 0 ]; then
    log_info "✅ Imagen construida: $APP_NAME:latest"
else
    log_error "Error construyendo imagen"
    exit 1
fi
echo ""

# ============================================================================
# Limpiar imágenes antiguas
# ============================================================================
log_info "Limpiando imágenes antiguas..."
docker image prune -f
log_info "✅ Imágenes antiguas limpiadas"
echo ""

# ============================================================================
# Iniciar contenedor
# ============================================================================
log_info "Iniciando contenedor con Docker Compose..."

docker-compose up -d

if [ $? -eq 0 ]; then
    log_info "✅ Contenedor iniciado"
else
    log_error "Error iniciando contenedor"
    exit 1
fi
echo ""

# ============================================================================
# Verificar estado
# ============================================================================
log_info "Verificando estado del contenedor..."
sleep 3

if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    log_info "✅ Contenedor corriendo"
    echo ""
    log_info "Últimos logs:"
    echo "----------------------------------------"
    docker logs --tail 20 $CONTAINER_NAME
    echo "----------------------------------------"
else
    log_error "El contenedor no está corriendo. Logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi
echo ""

# ============================================================================
# Instrucciones finales
# ============================================================================
echo ""
log_info "╔══════════════════════════════════════════════════╗"
log_info "║  ✅ DEPLOYMENT COMPLETADO                       ║"
log_info "╚══════════════════════════════════════════════════╝"
echo ""

log_info "📋 Para usar el CLI interactivo:"
log_info "   docker exec -it $CONTAINER_NAME python3 cyber_triage_cli.py"
echo ""

log_info "📊 Comandos útiles:"
log_info "   Ver logs:      docker logs -f $CONTAINER_NAME"
log_info "   Detener:       docker stop $CONTAINER_NAME"
log_info "   Reiniciar:     docker restart $CONTAINER_NAME"
log_info "   Shell:         docker exec -it $CONTAINER_NAME /bin/bash"
log_info "   Estadísticas:  docker stats $CONTAINER_NAME"
echo ""

log_info "🔧 Acceso interactivo al CLI:"
log_info "   docker exec -it $CONTAINER_NAME python3 cyber_triage_cli.py"
echo ""

log_info "╔══════════════════════════════════════════════════╗"
log_info "║  🚀 Sistema listo para usar                     ║"
log_info "╚══════════════════════════════════════════════════╝"
echo ""
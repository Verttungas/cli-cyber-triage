FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m -u 1000 cybertriage
WORKDIR /home/cybertriage/app

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY --chown=cybertriage:cybertriage . .

# Crear directorios
RUN mkdir -p data evidencia_temp logs prompts && \
    chown -R cybertriage:cybertriage /home/cybertriage/app

USER cybertriage

# Health check simple
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# Comando por defecto: ejecutar CLI
CMD ["python3", "cyber_triage_cli.py"]
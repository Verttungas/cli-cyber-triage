FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 cybertriage
WORKDIR /home/cybertriage/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=cybertriage:cybertriage . .

RUN mkdir -p data/incidents logs prompts && \
    chown -R cybertriage:cybertriage /home/cybertriage/app

USER cybertriage

HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD python3 -c "from db_manager import DatabaseManager; db = DatabaseManager(); print(db.get_database_stats())" || exit 1

CMD ["python3", "scheduler.py", "--daemon"]
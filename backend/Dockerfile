# Flask API. Build from the repository root so the dataset can be copied in:
#   docker build -f backend/Dockerfile -t paddle-finder-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PADDLE_DATA_FILE=/data/paddle_database.csv \
    AUTO_SEED=0

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY data/ /data/
COPY backend/ /app/
RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 5001
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/api/health')"

# Seed once (no-op when data exists), then serve with gunicorn.
CMD ["sh", "-c", "python -m paddle_finder.data.seed --if-empty && exec gunicorn --bind 0.0.0.0:5001 --workers 2 --access-logfile - wsgi:app"]

FROM python:3.12-slim AS base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000

# Development: hot reload with volume mount
FROM base AS development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production: multi-worker, no reload
FROM base AS production
RUN pip install --no-cache-dir gunicorn
CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "-w", "4", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "30"]

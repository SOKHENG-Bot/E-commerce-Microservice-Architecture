FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Install system dependencies (cached unless you change this list)
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (so pip install can be cached)
COPY ../requirements.txt ./user_service/requirements.txt
RUN pip install --no-cache-dir -r ./user_service/requirements.txt

# Copy app code (this will change most often, so put last)
COPY ../app ./user_service/app
COPY ../.env ./.env

# Create data directory for SQLite and set permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8001

# Start Uvicorn server
CMD ["uvicorn", "user_service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]

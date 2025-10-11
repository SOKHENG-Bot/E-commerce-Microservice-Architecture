FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app:/app/product_service

# Install system dependencies (cached unless you change this list)
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (so pip install can be cached)
COPY requirements.txt ./product_service/requirements.txt
RUN pip install --no-cache-dir -r ./product_service/requirements.txt

# Copy app code (this will change most often, so put last)
COPY app ./product_service/app

# Copy root .env file
COPY .env ./product_service/.env

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
# USER appuser  # Temporarily commented out for debugging

EXPOSE 8002

# Start Uvicorn server
CMD ["uvicorn", "product_service.app.main:app", "--host", "0.0.0.0", "--port", "8002"]

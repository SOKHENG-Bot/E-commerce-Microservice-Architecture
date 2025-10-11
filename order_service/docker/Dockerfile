FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY order_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire order_service directory to maintain module structure
COPY order_service/ ./order_service/

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "order_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

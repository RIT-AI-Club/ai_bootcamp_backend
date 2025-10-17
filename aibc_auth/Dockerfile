FROM python:3.11-slim

WORKDIR /app

# Set Pythonpath and other env vars
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install curl for health checks (Cloud Run health checks)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs && chmod -R 777 /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Run the application (Cloud Run uses PORT env var, defaults to 8080)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
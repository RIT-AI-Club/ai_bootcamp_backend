FROM python:3.11-slim

WORKDIR /app

# Set Pythonpath and other env vars
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs && chmod -R 777 /app/logs

EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
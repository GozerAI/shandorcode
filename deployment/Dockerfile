# ShandorCode Production Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY LICENSE.txt .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8765/api/current')" || exit 1

# Run server
CMD ["python", "-m", "src.api.server", "--host", "0.0.0.0", "--port", "8765"]

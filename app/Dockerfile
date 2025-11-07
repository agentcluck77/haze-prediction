# Multi-stage build for faster builds
FROM python:3.9-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Install Python dependencies with uv
RUN uv pip install --no-cache-dir --system -r requirements.txt

# Copy application code
COPY inference.py .

# Create output directory
RUN mkdir -p /data/output

# Default command
CMD ["python", "inference.py"]
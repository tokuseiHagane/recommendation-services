# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install UV
RUN pip install uv

# Copy dependency files and source code
COPY pyproject.toml README.md ./
COPY src ./src

# Install dependencies
RUN uv pip install --system -e .

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install bash for entrypoint script
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src ./src
COPY piccolo_conf.py .
COPY piccolo_conf_vk.py .

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Set entrypoint to apply migrations automatically
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["python", "-m", "src.Bootstrap"]

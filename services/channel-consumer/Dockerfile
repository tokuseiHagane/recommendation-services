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

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src ./src
COPY app.py .
COPY piccolo_conf.py .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run application with auto-tracing
CMD ["python", "-m", "src.Bootstrap"]

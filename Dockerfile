# Optimized Dockerfile for SQLite-based miHoYo Bot
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Bangkok
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set the working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/backups

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip cache purge

# Copy the application code
COPY . /app/

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash mihoyo \
    && chown -R mihoyo:mihoyo /app

# Switch to non-root user
USER mihoyo

# Expose port for health checks
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/mihoyo_bot.db').execute('SELECT 1')" || exit 1

# Default command
CMD ["python", "-m", "discord_bot.bot"]
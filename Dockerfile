FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
    libffi-dev \
    liblzma-dev \
    git \
    wget \
    curl \
    ffmpeg \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install yt-dlp and other Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create .env if not exists (default values)
RUN echo "# yt-dlp REST API Configuration" > .env \
    && echo "HOST=0.0.0.0" >> .env \
    && echo "PORT=8080" >> .env \
    && echo "AUTO_UPDATE_ENABLED=true" >> .env \
    && echo "UPDATE_CHECK_INTERVAL=3600" >> .env \
    && echo "LOG_LEVEL=INFO" >> .env

# Create cron job for auto-updates
RUN echo "0 */1 * * * pip install --upgrade yt-dlp >> /var/log/ytdlp-update.log 2>&1" > /etc/cron.d/ytdlp-update \
    && chmod 644 /etc/cron.d/ytdlp-update \
    && touch /var/log/ytdlp-update.log

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run cron and app
CMD cron && python app.py

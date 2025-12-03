FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl gnupg build-essential && \
    # Add NodeSource GPG key
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    # Add Node.js 20 LTS repository
    NODE_MAJOR=20 && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    # Install Node.js, FFmpeg, and Python dependencies
    apt-get update && \
    apt-get install -y nodejs ffmpeg libsodium-dev libffi-dev libopus0 libopus-dev && \
    # Clean up to reduce image size
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir PyNaCl && \
    pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py /app/

# Health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import discord; print('OK')" || exit 1

# Run the bot
CMD ["python", "-u", "bot.py"]
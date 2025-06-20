FROM python:3.10-slim

# Disable pip cache
ENV PIP_NO_CACHE_DIR=1

# Install system-level dependencies
RUN apt update && apt install -y --no-install-recommends \
    gcc \
    build-essential \
    ffmpeg \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libwebp-dev \
    libxml2-dev \
    libxslt1-dev \
    unzip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirement file and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Copy full bot project into container
COPY . .

# Run the Grabber module
CMD ["python3", "-m", "Grabber"]
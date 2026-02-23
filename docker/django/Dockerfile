FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.development \
    DJANGO_CONFIGURATION=Dev \
    SHELL=/bin/bash \
    DOCKER=true
# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    postgis \
    gettext \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    build-essential \
    inotify-tools \
    curl \
    # Specific dependencies from README
    imagemagick \
    libmagickwand-dev \
    libfreetype6-dev \
    poppler-utils \
    qpdf \
    ocrmypdf \
    libpango1.0-dev \
    libgeoip-dev \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy entire project
COPY . .

# Install repo dependencies
RUN chmod +x ./devsetup.sh && \
    ./devsetup.sh dependencies

# Compile messages
RUN python manage.py compilemessages -l de -i node_modules

EXPOSE 8000

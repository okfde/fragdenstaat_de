# Development Dockerfile with File Watching Optimizations
FROM python:3.12-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.development
ENV SHELL=/bin/bash

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
    wget \
    inotify-tools \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm@9.15.0 \
    && pnpm setup \
    && rm -rf /var/lib/apt/lists/*

# Configure pnpm global bin directory
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

# Install uv for Python package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Define repositories
# All repos that need Python installation
ENV REPOS="froide froide-campaign froide-legalaction froide-food froide-payment froide-crowdfunding froide-govplan froide-fax froide-exam django-filingcabinet froide-evidencecollection"
# Subset of repos that also need frontend installation
ENV FRONTEND_REPOS="froide froide-food froide-exam froide-campaign froide-payment froide-legalaction django-filingcabinet"
# Frontend directories for linking
ENV FRONTEND_DIR="froide froide-food froide-exam froide-campaign froide-payment froide-legalaction django-filingcabinet"
# Frontend package names for linking
ENV FRONTEND="froide froide_food froide_exam froide_campaign froide_payment froide_legalaction @okfde/filingcabinet"
# Repos with peer dependencies on froide
ENV FROIDE_PEERS="froide-campaign froide-food"

# Copy only requirements files first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies directly to system (no venv needed in Docker)
RUN uv pip install --system -r requirements-dev.txt

# Copy entire project (after Python dependencies)
COPY . .

# Install Python and frontend dependencies in a single pass
RUN for name in $REPOS; do \
        echo "Installing $name..."; \
        uv pip install --system -e "./$name" --config-setting editable_mode=compat; \
        case "$name" in \
            froide|froide-food|froide-exam|froide-campaign|froide-payment|froide-legalaction|django-filingcabinet) \
                echo "Installing frontend dependencies for $name..."; \
                cd /app/$name && pnpm install; \
                cd /app ;; \
        esac \
    done

# Setup main project
RUN cd /app && pnpm install

# Setup frontend package linking (mimicking devsetup.sh)
RUN echo "Setting up frontend package linking..." && \
    # Link all frontend packages globally first
    for name in $FRONTEND_DIR; do \
        echo "Linking $name globally..."; \
        cd /app/$name && pnpm link --global; \
        cd /app; \
    done && \
    # Link froide peer dependencies
    for name in $FROIDE_PEERS; do \
        echo "Linking froide peer dependency for $name..."; \
        cd /app/$name && pnpm link --global froide; \
        cd /app; \
    done && \
    # Link dependencies into main project
    cd /app && \
    for name in $FRONTEND; do \
        echo "Linking $name into main project..."; \
        pnpm link --global "$name"; \
    done && \
    echo "Frontend linking completed."

# Compile messages
RUN python manage.py compilemessages -l de -i node_modules

# Expose ports
EXPOSE 8000 5173

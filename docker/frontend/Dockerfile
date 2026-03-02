FROM node:22-bookworm-slim

# Set up pnpm home directory
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="${PNPM_HOME}:${PATH}"
ENV DOCKER=true

# Enable corepack
RUN corepack enable

# Set work directory
WORKDIR /app

# Copy content
COPY . ./

# Dynamically prepare pnpm version and activate
RUN pnpm_version=$(node -p "require('./package.json').packageManager?.replace('pnpm@', '')") && \
    echo "Using pnpm version: $pnpm_version" && \
    corepack prepare "pnpm@$pnpm_version" --activate

# Install dependencies and run frontend setup
RUN chmod +x ./devsetup.sh && \
    ./devsetup.sh frontend

EXPOSE 5173

CMD ["pnpm", "run", "dev"]

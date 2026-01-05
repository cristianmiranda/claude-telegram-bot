FROM python:3.12-slim

# Install Node.js (required for Claude Code CLI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nodejs \
        npm \
        git \
        curl \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install bot package
WORKDIR /bot
COPY pyproject.toml .
COPY *.py ./
RUN pip install --no-cache-dir .

# Create non-root user (Claude CLI refuses --dangerously-skip-permissions as root)
RUN useradd -m -s /bin/bash claude && \
    mkdir -p /home/claude/.claude && \
    chown -R claude:claude /home/claude && \
    chmod -R 755 /bot

# Runtime working directory (project mounts here)
WORKDIR /app

# Switch to non-root user
USER claude

ENTRYPOINT ["python", "/bot/__main__.py", "--config", "/app/.env"]
